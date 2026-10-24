import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_profile as u

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
COMMIT = {'oid':'a'*40,'additions':120,'deletions':20,'authoredDate':'2026-10-20T10:00:00Z'}
def repo(name='app', **changes):
    return {'id':name,'nameWithOwner':f'{u.LOGIN}/{name}','isPrivate':False,'isFork':False,'stargazerCount':2,'defaultBranchRef':{'target':{'oid':'b'*40}},**changes}
def connection(nodes, next_page=False, cursor=None):
    return {'nodes':nodes,'pageInfo':{'hasNextPage':next_page,'endCursor':cursor}}
class Fake:
    def __init__(self, repos=None):
        self.repos = repos if repos is not None else [repo()]
        self.histories = 0
    def query(self, query, variables):
        if query == u.ACCOUNT:
            return {'user':{'id':'user-id','login':u.LOGIN,'followers':{'totalCount':3}}}
        if query == u.REPOSITORIES:
            return {'user':{'repositories':connection(self.repos)}}
        if query == u.HISTORY:
            self.histories += 1
            return {'repository':{'object':{'history':connection([copy.deepcopy(COMMIT)])}}}
        if query == u.LANGUAGES:
            return {'repository':{'languages':{'edges':[{'size':500,'node':{'name':'TypeScript','color':'#3178c6'}}],'pageInfo':{'hasNextPage':False,'endCursor':None}}}}
        raise AssertionError(query)
class StatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)/'cache.json'
    def test_totals_and_calendar(self):
        data, _ = u.collect(Fake(), self.cache, NOW)
        self.assertEqual((data['commits'],data['additions'],data['deletions']),(1,120,20))
        self.assertEqual(data['activity'][0]['month'],'2025-11')
        self.assertEqual(data['activity'][-1],{'month':'2026-10','commits':1})
        self.assertEqual(data['active_days'],1)
        self.assertEqual(data['languages'][0]['bytes'],500)
    def test_profile_forks_private_and_foreign_exclusions(self):
        data, _ = u.collect(Fake([repo(),repo(u.LOGIN),repo('fork',isFork=True),repo('secret',isPrivate=True),repo('foreign',nameWithOwner='other/app')]),self.cache,NOW)
        self.assertEqual(data['public_repos'],3)
        self.assertEqual(data['scanned_repositories'],1)
        self.assertEqual(data['commits'],1)
        self.assertEqual(data['stars'],6)
    def test_same_commit_is_not_double_counted_across_repositories(self):
        data, _ = u.collect(Fake([repo('one'),repo('two')]),self.cache,NOW)
        self.assertEqual(data['commits'],1)
        self.assertEqual(data['additions'],120)
    def test_empty_repository(self):
        client=Fake([repo(defaultBranchRef=None)])
        data,_=u.collect(client,self.cache,NOW)
        self.assertEqual(data['commits'],0)
        self.assertEqual(client.histories,0)
    def test_cache_reused_with_same_immutable_head(self):
        client=Fake();_,cache=u.collect(client,self.cache,NOW)
        self.cache.write_text(json.dumps(cache));u.collect(client,self.cache,NOW)
        self.assertEqual(client.histories,1)
    def test_changed_head_invalidates_cache(self):
        client=Fake();_,cache=u.collect(client,self.cache,NOW)
        self.cache.write_text(json.dumps(cache));client.repos[0]['defaultBranchRef']['target']['oid']='c'*40
        u.collect(client,self.cache,NOW)
        self.assertEqual(client.histories,2)
    def test_cache_is_keyed_by_identity_not_position(self):
        client=Fake([repo('one'),repo('two')]);_,cache=u.collect(client,self.cache,NOW)
        self.cache.write_text(json.dumps(cache));client.repos.reverse();u.collect(client,self.cache,NOW)
        self.assertEqual(client.histories,2)
    def test_corrupt_or_foreign_cache_ignored(self):
        for text in ['not json',json.dumps({'schema':1,'author':'different','repositories':{}})]:
            self.cache.write_text(text)
            self.assertEqual(u.load_cache(self.cache,'user-id'),{})
    def test_invalid_commits_rejected(self):
        for change in [{'additions':-1},{'deletions':True},{'authoredDate':'invalid'},{'oid':'bad'}]:
            self.assertFalse(u.cache_valid({'head':'head','commits':[{**COMMIT,**change}]},'head'))
        self.assertFalse(u.cache_valid({'head':'head','commits':[COMMIT,COMMIT]},'head'))
    def test_pagination(self):
        calls=[]
        def fetch(cursor):
            calls.append(cursor)
            return connection([1],True,'next') if cursor is None else connection([2])
        self.assertEqual([item for page in u.pages(fetch) for item in page['nodes']],[1,2])
        self.assertEqual(calls,[None,'next'])
    def test_repeated_or_missing_cursor_fails(self):
        for cursor in [None,'again']:
            with self.assertRaises(u.StatsError):list(u.pages(lambda _:connection([],True,cursor)))
    def test_future_commit_not_in_activity(self):
        with patch.dict(COMMIT,{'authoredDate':'2030-01-01T00:00:00Z'}):
            data,_=u.collect(Fake(),self.cache,NOW)
            self.assertEqual(sum(item['commits'] for item in data['activity']),0)
            self.assertEqual(data['active_days'],0)
    def test_atomic_write(self):
        path=Path(self.temp.name)/'nested/file.json';u.atomic_write(path,'first');u.atomic_write(path,'second')
        self.assertEqual(path.read_text(),'second');self.assertEqual(len(list(path.parent.iterdir())),1)
    def test_api_graphql_errors_are_not_silently_accepted(self):
        with patch('subprocess.run') as run, patch('time.sleep'):
            run.return_value.returncode=0;run.return_value.stdout='{"errors":[{"message":"failed"}],"data":{}}'
            with self.assertRaises(u.StatsError):u.GitHub().query('',{})
            self.assertEqual(run.call_count,3)
    def test_api_retries_transient_failure(self):
        with patch('subprocess.run') as run,patch('time.sleep'):
            from subprocess import CompletedProcess
            run.side_effect=[CompletedProcess([],1,'',''),CompletedProcess([],0,'{"data":{"ok":true}}','')]
            self.assertEqual(u.GitHub().query('',{}),{'ok':True})
    def test_commit_history_paginates(self):
        client=Fake()
        original=client.query
        def query(q,v):
            if q != u.HISTORY:return original(q,v)
            return {'repository':{'object':{'history':connection([COMMIT],True,'next') if v['cursor'] is None else connection([{**COMMIT,'oid':'d'*40}])}}}
        client.query=query
        self.assertEqual(len(u.history(client,repo(),'user-id')),2)
    def test_language_bytes_paginates(self):
        client=Fake()
        def query(q,v):
            return {'repository':{'languages':{'edges':[{'size':1,'node':{'name':'CSS' if v['cursor'] else 'HTML','color':None}}],'pageInfo':{'hasNextPage':v['cursor'] is None,'endCursor':'next'}}}}
        client.query=query
        self.assertEqual(len(u.language_bytes(client,repo())),2)

if __name__=='__main__':unittest.main()
