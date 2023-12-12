from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from lxml import html
from lxml import etree
import re
from enum import Enum
from rekkasync.rekkasync import Manager
import json
from json import JSONDecodeError
import pandas as pd


class Move:
    def __init__(self,**kwargs):
        #dict = self.__rename(kwargs)
        #keys = list(kwargs.keys())
        #for key in keys:
        #    val = kwargs[key]
        #    del kwargs[key]
        #    kwargs[key.lower()] = val
            
        self.__dict__.update(kwargs)

    def __rename(self,dict):
        new_dict = {}
        for x in dict:
            value = dict[x]
            try:
                value = int(value)
            except ValueError:
                pass
            except TypeError:
                pass
            if x == 'src':
                vals = [Notation[v.split('/')[-1].split('.')[0].replace('-','_')].value[1] for v in value if v != '']
                new_dict['notation'] = vals
            else:
                try:
                    name = Names[x.split(' ')[0]].value
                    new_dict[name] = value
                except KeyError:
                    name = x
                    new_dict[name] = value

        return new_dict

    def __repr__(self):
        items = (f"{k}={v!r}\n" for k, v in self.__dict__.items())
        return "{}".format(''.join(items))

    def __eq__(self, other):
        if isinstance(self, SimpleNamespace) and isinstance(other, SimpleNamespace):
           return self.__dict__ == other.__dict__
        return NotImplemented

    def __getitem__(self,item):
        return getattr(self,item)

    def to_dict(self):
        return self.__dict__

class Names(Enum):
    frame_fixed_m__F0yxc = 'name'
    frame_startup_frame__IeKL6 = 'startup'
    frame_active_frame__1pLtR = 'active'
    frame_recovery_frame__WLqFt = 'recovery'
    frame_hit_frame__7cQT6 = 'on-hit'
    frame_block_frame___DOYN = 'on-block'
    frame_cancel__0oYdZ = 'cancel properties'
    frame_damage__D0g1H = 'damage'
    frame_combo_correct__7WrWM = 'scaling'
    frame_drive_gauge_gain_hit__C2Gty = 'drive gauge gain'
    frame_drive_gauge_lose_dguard__lc_Xg = 'blocked gauge drain'
    frame_drive_gauge_lose_punish__HTOzt = 'punish counter gauge drain'
    frame_sa_gauge_gain__e0GRR= 'super meter gain'
    frame_attribute__javf9 = 'properties'
    frame_note__6XAiP = 'note'
    frame_classic__OHge5 = 'notation'

class Notation(Enum):
    icon_punch = ['Punch','p']
    icon_kick = ['Kick','k']
    icon_punch_l = ['Light Punch','lp']
    icon_punch_m = ['Medium Punch','mp']
    icon_punch_h = ['Heavy Punch','hp']
    icon_kick_l = ['Light Kick','lk']
    icon_kick_m = ['Medium Kick','mk']
    icon_kick_h = ['Heavy Kick','hk']
    key_d = ['Down','2']
    key_dc = ['Down Charge','[2]']
    key_dl = ['Down Back','1']
    key_dlc = ['Down Back Charge','[1]']
    key_l = ['Back','4']
    key_lc = ['Back Charge','[4]']
    key_ul = ['Up Back','7']
    key_ulc = ['Up Back Charge','[7]']
    key_u = ['Up','8']
    key_uc = ['Up Charge','[8]']
    key_ur = ['Up Forward','9']
    key_urc = ['Up Forward Charge','[9]']
    key_r = ['Forward','6']
    key_rc = ['Forward Charge','[6]']
    key_dr = ['Down Forward','3']
    key_drc = ['Down Forward Charge','[3]']
    key_plus = ['+','+']   
    key_or = ['Or','|']
    arrow_3 = ['Then','~']
    key_nutral = ['Neutral','n']

def pull_moves(tree):
    tables = []
    new_tree = tree.xpath('//div/section/div/section/article')
    tps = tree.xpath('.//div/section//h3/span/text()')
    i = tps[0]
    tps = tps[1:]
    tps.append(i)
    count = 1
    index = 0
    for x in new_tree:
        
        headers = x.xpath('./table/thead//tr//th/text()')
        body =  x.xpath('./table/tbody/tr')
        moves = []
        for row in body:
            #print(row.tag)
            cols = row.xpath('./td')
            #print(str(len(cols)) + ' ' + str(len(headers)))
            #print(cols.text_content())
            tx = {}
            for y in range(len(cols)):
                t = cols[y].text_content()
                if t == '': t='-'
                try:
                    tx[headers[y].replace(' ','_')] = t.replace('+','')
                except IndexError:
                    print(headers)
                    print(cols.text_content())
                    raise IndexError
            #tx['type'] = tps[index]
            moves.append(tx)
        tables.append(moves)
        count += 1
        if count % 5 == 0: index +=1
    return tables

class Movelist():

    def __init__(self,li):
        self.li = li
        self.mappings = {}
        index = 0
        for move in self.li:
            self.mappings[move.input] = index
            index += 1

    def __getitem__(self,item):
        if type(item) == int:
            return self.li[item]
        elif type(item) == str:
            return self.li[self.mappings[item]]

    def query(self,query):
        regex = re.search('([^<>=]+)([<>=]+)([^<>=]+)',query)
        matches = []
        for item in self.li:
            if self.__compare(*regex.groups(),item):
                matches.append(item)
        return matches

    def sql(self,query):
        regex = re.search('select (.+)where (.+)',query.lower())
        comparisons = regex.group(2).split('and')
        reg = '([^<>!=]+)([<>!=]+)([^<!>=]+)'
        comparisons = [re.search(reg,comp).groups() for comp in comparisons]
        results = []
        for item in self.li:
            matches = True
            for comparison in comparisons:
                if not self.__compare(*comparison,item):
                    matches = False
                    break
            if matches:
                results.append(self.__select(regex.group(1),item))
        return results

    def __select(self,names,item):
        names = names.strip()
        if names == '*':
            return item
        names = names.split(',')
        vals = {}
        for name in names:
            vals[name.strip()] = item[name.strip()]
        return Move(**vals)
    
    def __compare(self,key,comparator,val,item):
        val = val.strip()
        #try:
            #val = int(val)
        #except ValueError:
        #    pass
        try:
            it = item[key.strip()]
        except AttributeError:
            return False
        try:
            it = it.lower()
        except AttributeError:
            pass
        try:
            if comparator == '<':
                return it < val
            elif comparator == '>':
                return it > val
            elif comparator == '=' or comparator == '==':
                return it == val
            elif comparator == '<=':
                return it <= val
            elif comparator == '>=':
                return it >= val
            elif comparator == '!=':
                return it != val
            else:
                raise ValueError('Ensure you are using a valid comparator')
        except TypeError as e:
            pass
        
            

    def keys(self):
        return self.mappings.keys()

def make_moves():
    tree = html.fromstring(source)
    tables = pull_moves(tree)    

    moves = []
    for table in tables:
        for move in table:
            moves.append(move)
    
    final_moves = []
    
    loop = True
    index = 0
    while loop:
        match = moves.pop(index)
        inner_loop = True
        inner_index = 0
        while inner_loop:
            try:
                if match['input'] == moves[inner_index]['input']:
                    match |= moves.pop(inner_index)
            except IndexError:
                inner_loop = False
            inner_index +=1
        final_moves.append(Move(**match))
        if len(moves) <= 0:
            loop = False
    moves = Movelist(final_moves)
    return moves

def get_source():
    driver = webdriver.Chrome()# Open the website
    driver.get("https://wiki.supercombo.gg/w/Street_Fighter_6/Guile/Frame_data")
    source = driver.page_source
    driver.close()
    return source