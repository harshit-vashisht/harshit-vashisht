import copy
import json
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_card import render_card
from update_profile import readme
NS={'s':'http://www.w3.org/2000/svg'}
STATS={'login':'harshit-vashisht','updated_at':'2026-10-24T12:00:00Z','public_repos':6,'commits':6,'followers':0,'stars':0,'additions':7138,'deletions':24,'active_days':4,'scanned_repositories':5,'stack':['React','TypeScript','Vite','GSAP','Python','HTML / CSS','GitHub Actions'],'languages':[{'name':'TypeScript','bytes':80000,'color':'#3178c6'},{'name':'HTML','bytes':12000,'color':'#e34c26'}],'activity':[{'month':f'2026-{i:02d}','commits':i} for i in range(1,11)]}
class CardTests(unittest.TestCase):
    def test_both_themes_are_valid_svg(self):
        for theme in ['light','dark']:
            root=ET.fromstring(render_card(STATS,theme))
            self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
            self.assertEqual(root.get('viewBox'),'0 0 1100 1050')
            self.assertEqual(root.get('data-theme'),theme)
    def test_same_content_in_both_themes(self):
        def text(theme):
            return [node.text for node in ET.fromstring(render_card(STATS,theme)).iter() if node.tag.endswith(('text','title','desc'))]
        self.assertEqual(text('light'),text('dark'))
    def test_no_active_or_external_content(self):
        root=ET.fromstring(render_card(STATS,'light'))
        for node in root.iter():
            self.assertNotIn(node.tag.split('}')[-1],['script','foreignObject','image','a'])
            self.assertFalse(any(key.lower().startswith('on') or key.endswith('href') for key in node.attrib))
        self.assertNotIn('@import',render_card(STATS,'light'))
    def test_reduced_motion_and_static_content(self):
        svg=render_card(STATS,'dark')
        self.assertIn('prefers-reduced-motion: reduce',svg)
        self.assertIn('animation: none',svg)
        self.assertNotIn('opacity: 0;',svg)
    def test_exact_counts_and_scope_are_accessible(self):
        root=ET.fromstring(render_card(STATS,'light'))
        description=root.find('s:desc',NS).text
        for value in ['7,138','24','default branches','excluding this profile','not unique lines','Created by atulhacks']:
            self.assertIn(value,description)
    def test_untrusted_text_and_colors_cannot_create_elements(self):
        data=copy.deepcopy(STATS);data['login']='<script>alert(1)</script>';data['stack']=['<image href="https://invalid">'];data['languages']=[{'name':'A&B<script>','bytes':1,'color':'red" onload="alert(1)'}]
        root=ET.fromstring(render_card(data,'light'))
        self.assertEqual(len(root.findall('.//s:script',NS)),0)
        self.assertEqual(len(root.findall('.//s:image',NS)),0)
    def test_empty_data_is_renderable(self):
        svg=render_card({'login':'harshit-vashisht'},'dark')
        ET.fromstring(svg);self.assertIn('No language data',svg);self.assertNotIn('NaN',svg)
    def test_large_counts_are_compact_with_exact_description(self):
        data={**STATS,'additions':1234567890,'commits':1000000}
        svg=render_card(data,'light');self.assertIn('1.2B',svg);self.assertIn('1,234,567,890',svg)
    def test_invalid_theme_rejected(self):
        with self.assertRaises(ValueError):render_card(STATS,'unknown')
    def test_path_move_has_two_coordinates(self):
        root=ET.fromstring(render_card(STATS,'light'))
        for node in root.findall('.//s:path',NS):
            self.assertNotRegex(node.get('d',''),r'^M\d+[vVhH]')
    def test_readme_theme_switch_and_only_correct_identity(self):
        text=readme(STATS)
        self.assertIn('prefers-color-scheme: dark',text);self.assertIn('prefers-color-scheme: light',text)
        self.assertIn('7138',text.replace(',',''))
        self.assertIn('https://harshit-vashisht.github.io/',text)
        self.assertIn('Created by [atulhacks](https://github.com/atulhacks)',text)
if __name__=='__main__':unittest.main()
