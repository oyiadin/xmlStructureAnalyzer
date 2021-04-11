# coding=utf-8
# Author: hsiaoxychen <i@chenxy.me>
# Date: 2021-04-11
# Website: https://chenxy.me/

import random
from dataclasses import dataclass, field

from lxml import etree
from typing import List, Optional, Dict


MAX_ATTR_VALUE = 10
MAX_TAG_TEXT = 10


@dataclass
class Structure:
    tag: str
    parent: 'Structure' = None
    attrs: 'Dict[str, Attribute]' = field(default_factory=dict)
    children: 'Dict[str, Structure]' = field(default_factory=dict)
    times: int = 0
    texts: List[str] = field(default_factory=list)
    too_much_texts: bool = field(repr=False, default=False)


@dataclass
class Attribute:
    name: str
    parent: 'Structure'
    required: bool = True
    times: int = 1
    values: List[str] = field(default_factory=list)
    too_much_values: bool = field(repr=False, default=False)


class DTDResolver(etree.Resolver):
    def resolve(self, system_url, public_id, context):
        # return self.resolve_filename(os.path.join(".", system_url), context)
        return self.resolve_filename("dblp.dtd", context)


it = etree.iterparse('dblp-2021-03-01.xml', ['start', 'end'], load_dtd=True)
it.resolvers.add(DTDResolver())


root = Structure('fake-root', times=1)
curr = root


def dump_attr(attr: Attribute):
    if attr.required:
        ans = '%s|required' % attr.name
    else:
        ans = '%s' % attr.name
    if attr.values:
        ans += ('|enum[%s]' % ('; '.join(attr.values)))
    return ans


def dump_node(f, node: Structure = root, depth=0):
    descriptions = {}
    if node.attrs:
        descriptions['Attrs'] = ', '.join([
            dump_attr(attr) for attr in node.attrs.values()])
    if node.texts:
        descriptions['Texts'] = node.texts

    description = '; '.join(['%s=%s' % (k, v) for k, v in descriptions.items()])

    short_description = ''
    if node.parent:
        if node.times == node.parent.times:
            short_description = ' required'
        elif node.times > node.parent.times:
            short_description = ' multiple'
        elif node.times / node.parent.times < 0.05:
            short_description = ' rarely'
    if description:
        f.write('%s- %s%s [%s]\n' % (' '*depth, node.tag, short_description, description))
    else:
        f.write('%s- %s%s\n' % (' '*depth, node.tag, short_description))

    if node.children:
        for child in node.children.values():
            dump_node(f, child, depth+1)

count = 1000000


for event, elem in it:
    count -= 1
    if event == 'start':
        if elem.tag not in curr.children:
            child = Structure(elem.tag, parent=curr)
            curr.children[elem.tag] = child
            curr = child
        else:
            curr = curr.children[elem.tag]
        curr.times += 1
    elif event == 'end':
        for key, value in elem.attrib.items():
            if key not in curr.attrs:
                attr = Attribute(key, parent=curr, values=[value])
                curr.attrs[key] = attr
            else:
                attr = curr.attrs[key]
                attr.times += 1
                if not attr.too_much_values and value not in attr.values:
                    if len(attr.values) < MAX_ATTR_VALUE and len(value) < 20:
                        attr.values.append(value)
                    else:
                        attr.too_much_values = True
                        attr.values = []
        not_found_keys = curr.attrs.keys() - elem.attrib.keys()
        for key in not_found_keys:
            curr.attrs[key].required = False
        text = (elem.text or '').strip()
        if text and not curr.too_much_texts and text not in curr.texts:
            if len(curr.texts) < MAX_TAG_TEXT and len(text) < 20:
                curr.texts.append(text)
            else:
                curr.too_much_texts = True
                curr.texts = []
        curr = curr.parent
        elem.clear()
    else:
        raise NotImplementedError

    if count == 0:
        count = 15000000
        print('sourceline', elem.sourceline, 'percent', (int(elem.sourceline / 75520693 * 1000) / 10))
        # class X:
        #     def write(self, x):
        #         print(x)
        with open('structure-%s.txt' % ''.join(random.sample("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", 8)), 'w') as f:
            dump_node(f, list(root.children.values())[0])


with open('structure-final-%s.txt' % ''.join(random.sample("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", 8)), 'w') as f:
    dump_node(f, list(root.children.values())[0])

