#!/usr/bin/env python

# This script counts references and show most citied articles
# Usage: 'python freq.py cond-mat.17'


from collections import Counter
from sys import argv, path
from pprint import pprint
import pickle
import re
import os

path.insert(0, os.path.dirname(
                    os.path.realpath(__file__)) + '/extra')
import shared
import config


n_top = 30
volume = None
n_proc_articles = config.n_articles


def starts_with(str, sub_str):
    if sub_str == str[:len(sub_str)]: return True
    else: return False


def find_str(s_str, lines):
    for line in lines:
        if line.find(s_str) > -1: return True
    return False


def is_similar_refs(authors_list, year_list, ref_one, ref_two, min_intersect_len=None):
    authors_one, year_one = authors_list[ref_one], year_list[ref_one]
    authors_two, year_two = authors_list[ref_two], year_list[ref_two]

    if min_intersect_len is None:
        min_intersect_len = max(len(authors_one), len(authors_two))

    if year_one == year_two and \
        len(list(set(authors_one) & set(authors_two))) >= min_intersect_len:
        return True
    else:
        return False


def write_list(fn, ls):
    file = open(fn, "w+")
    for line in ls:
        file.write("{}\n".format(line))
    file.close()


def extract_journal_info(ref):
    journal_marks = "Phys. Appl. Rev. JETP Fiz. Lett. Nature J. " \
         "Physical Review Letters IEEE Journal Phys " \
         "Physica Science Europhys.".split()

    j_exp1 = re.compile(r'(?<=,).*?(?=,)')    # ex: ',Target,'
    j_exp2 = re.compile('[0-9]+') # checking number

    journal = None
    j_res1 = j_exp1.findall(ref)
    for k, r in enumerate(j_res1):
        j_res2 = j_exp2.findall(r)
        if len(j_res2) > 0:
            if len(list(set(j_res1[k].split())
                                & set(journal_marks))) > 0:
                journal = j_res1[k].strip()
    return journal


# FIXME: function is too big
import random
def count_refs():
    print("Extracting refs...")

    global_ref_list = []

    section, year = volume.split(".")
    texts_path = "../arxiv/{0}/{1}/".format(section, year)

    if not os.path.isfile('cache/{}.cache'.format(volume)):
        print(os.path.isfile('cache/{}.cache'.format(volume)))
        files_list = shared.random_glob(texts_path, n_proc_articles)
    else:
        with open('cache/{}.cache'.format(volume), 'rb') as f:
            d = pickle.load(f)
            files_list = d.keys()
            files_list = random.sample(files_list, n_proc_articles)

    for g, file in enumerate(files_list):
        content = open(file, "r").readlines()

        reflines = []

        exp = re.compile(r'^\[([0-9]+)\]')  # ex: [23] [14] [6]
        for j, line in enumerate(content):
            fstr = exp.findall(line)
            if len(fstr) == 1:
                reflines.append([int(fstr[0]), j])

        # get ending?

        refs = []
        for p, line in enumerate(reflines[:-1]):
            delta = reflines[p+1][1] - reflines[p][1]
            firstline = reflines[p][1]
            res = " ".join([content[firstline + t]
                            for t in range(delta)]).replace("\n", "")
            refs.append(re.sub(r'^\[[0-9]+\]', '', res))

        global_ref_list += refs


    global_ref_list = [x for x in global_ref_list if len(x) < 100]

    # authors
    exp1 = re.compile(r'[A-Z]\.+ [A-Z]\.+ [A-Za-z]+') # ex: 'J. M. Luttinger' 'A. A. Abrikosov'
    exp2 = re.compile(r'[A-Z]\.+ [A-Za-z]{2,}') # ex: 'M. Luttinger' 'A. Abrikosov', 2 because of Chinese researches

    # TODO: add new regular expressions
    # '[A-Za-z]+ [A-Z]\.\s*[A-Z]\.+' ex: 'Purcell E.M.' 'Purcell E. M.'
    # '[A-Za-z]+ [A-Z]\.' ex: 'Landau L.'
    # '[A-Z]{1,1}[a-z]+, [A-Z]{1,1}' ex: 'Lee, W.'
    # '\s* ([0-9]{4,4})' ex: ' 2007'

    # year
    # FIXME
    exp3 = re.compile(r'\(([0-9]+)\)') # ex: '(2016)' '(2005)'

    cov_cnt = 0
    a_list = []
    y_list = []

    accept_refs = []
    decline_refs = []

    print("Processing refs...")

    for i, ref in enumerate(global_ref_list):
        if i % 1000 == 0 and i > 0:
            print(i, len(global_ref_list))

        # authors
        res1 = exp1.findall(ref)
        res2 = exp2.findall(ref)

        # exp2 subset of exp1, here we delete intersection
        authors_list = res1
        for author in res2:
            if not find_str(author, authors_list):
                authors_list.append(author)

        # year
        res3 = exp3.findall(ref)
        if len(res3) > 1: res3 = [res3[0]]

        if len(authors_list) > 0 and res3:
            cov_cnt += 1
            accept_refs.append("{}".format(ref))
            a_list.append(authors_list)
            y_list.append(res3)
        else:
            decline_refs.append("{}".format(ref))

    print("Counting pairs...")

    cnt_d = {}
    for j in range(len(a_list)):
        if j % 1000 == 0 and j > 0:
            print(j, len(a_list))

        # format: 'Author1 & Author2 & ... & AuthorN & Year'
        cur_ref = j
        is_similar = False

        for probe_ref in cnt_d.keys():

            if is_similar_refs(a_list, y_list, probe_ref, cur_ref):
                cnt_d[probe_ref] += 1
                break

        if not is_similar: cnt_d[cur_ref] = 1

    if n_proc_articles == config.n_articles_debug:
        write_list(config.ref_stat + "accept_refs.txt", accept_refs)
        write_list(config.ref_stat + "decline_refs.txt", decline_refs)

    relevant_refs = ["{}, {}, {}".format(" & ".join(a_list[x]), int(y_list[x][0]), cnt_d[x])
                     for x in sorted(cnt_d, key=cnt_d.get,reverse=True)
                     if cnt_d[x] > 1]

    pprint(relevant_refs[:n_top])

    write_list("{}{}.txt".format(config.ref_stat, volume), relevant_refs)

    print("n_articles", n_proc_articles)
    print("accept_refs", len(accept_refs))
    print("decline_refs", len(decline_refs))
    print("top_cnt_sum", sum([z[1] for z in Counter(cnt_d).most_common(n_top)]))


def arg_run():
    if len(argv) < 2:
        print("Error: too few arguments")
    elif len(argv) > 3:
        print("Error: too many arguments")
    else:
        global volume
        volume = argv[1]

        s, y = volume.split(".")
        y = int(y)

        if "-d" in argv:
            global n_proc_articles
            n_proc_articles = config.n_articles_debug

        shared.create_dir(config.ref_stat)
        count_refs()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    shared.create_dir(config.ref_stat)
    arg_run()
