import nltk
import numpy as np
import re
import freeling
import configparser

"""
Personal Notes:
    NC -> Name Complete
    N -> Name
    A -> Surname
    AA -> Common Name
    AG -> Typo Name
    I -> Initial
    AD -> Particle Name
    AAA -> Main Last Name
    
    Terminal nodes in the Chompsky Normal Form:
    I , AA, AG, AD

NOTE:
    The working path is unoporuno_scrapy
"""


class NameParser:
    def __init__(self):
        self.grammar_head = """
                            NC -> N A
                            N -> N I
                            N -> N AA
                            N -> I
                            N -> AA
                            N -> AG
                            N -> AA AD
                            A -> AAA
                            A -> AAA AA
                            A -> AAA AD
                            A -> AAA AG
                            A -> AAA I
                            AAA -> AA
                            AAA -> AG
                            AAA -> AD
                            """
        self.name_tokenizer_regex = r'(Mc[A-Z][a-z]+|O\'[A-Z][a-z]+|[Dd]e\s[Ll]a\s[A-Z][a-z]+|-' \
                                    r'[Dd]e-[A-Z][a-z]+|[A-Z][a-z]+-[A-Z][a-z]+|[Dd]e\s[Ll]a' \
                                    r'\s[A-Z][a-z]+|[Vv][oa]n\s[A-Z][a-z]+|[Dd]e[l]?\s[A-Z][a-z]' \
                                    r'+|[A-Z][\.\s]{1,1}|[A-Z][a-z]+|[Dd]e\s[Ll]os\s[A-Z][a-z]+)'

        self.regexp_tagger_list = [(r'([A-Z][a-z]+-[A-Z][a-z]+|-[Dd]e-[A-Z][a-z]+)', 'AG'),
                                   (r'[A-Z][a-z]+', 'AA'),
                                   (r'[A-Z][\.\s]{1,1}', 'I'),
                                   (r'([A-Z][a-z]+-[A-Z][a-z]+|[Dd]e\s[Ll]a\s[A-Z][a-z]+|[Vv][oa]n'
                                   r'\s[A-Z][a-z]+|[Dd]e[l]?\s[A-Z][a-z]+|[Dd]e\s[Ll]os\s[A-Z][a-z]+)',
                                    'AD'),
                                   (r'(Mc[A-Z][a-z]+|O\'[A-Z][a-z]+)', 'AA')]

        self.tokenizer = nltk.RegexpTokenizer(self.name_tokenizer_regex)
        self.tagger = nltk.RegexpTagger(self.regexp_tagger_list)

    def parse(self, name):
        tokens = self.tokenizer.tokenize(name)
        tag_tokens = self.tagger.tag(tokens)
        terminals = ''
        for ts in tag_tokens:
            terminals += ts[1] + " -> " + "'" + ts[0] + "'" + "\n    "
        grammar_rules = self.grammar_head + terminals
        grammar = nltk.CFG.fromstring(grammar_rules)
        parser = nltk.ChartParser(grammar)
        return parser.parse(tokens)


class FeatureFilter:

    def __init__(self, base_name):
        self.base_name = base_name

    def get_nominal_vector(self, snippet):
        nominal = NominalFilter(self.base_name)
        return nominal.filter(snippet)


class NominalFilter:

    def __init__(self, name):
        name = Cleaner.remove_accent(Cleaner(), name)
        name = Cleaner.clean_reserved_xml(Cleaner(), name)
        self.tree = NameParser.parse(NameParser(), name)
        self.list_regex = self._name_variations()

        self.dic_vect = {'L': 0, 'C': 1, 'E': 2, 'X': 3, 'V': 4}

    def _add_variation(self, reg, variation, label):

        if variation.get(label) is None:
            variation[label] = []

        if reg not in variation.get(label):
            variation.get(label).append(reg)

    def _compression(self, cn, la):

        list_reg = []

        name = ""
        lastname = ""

        partition = '[\s-]+?'
        partition2 = '[\s]+?'
        for a in la:
            if lastname == "":
                lastname = a
            else:
                lastname += partition + a

        partition = '\.?[\s]*?'


        for n in cn:
            n = n[0]
            if name=="":
                name = n
            else:
                name += partition + n
            list_reg.append(n + partition + la[0])
            list_reg.append(la[0] + partition2 + n + partition)
            list_reg.append(n + partition + lastname)
            list_reg.append(lastname + partition2 + n + partition)

        list_reg.append(name + partition + la[0])
        list_reg.append(la[0] + partition2 + name + partition)
        list_reg.append(name + partition + lastname)
        list_reg.append(lastname + partition2 + name + partition)

        for reg in list_reg:
            yield reg

    def _expansion(self, en, la, initials):

        list_reg = []

        name = ""
        lastname = ""

        partition = "[a-z]+"
        partition2 = "[\s-]+?"

        for n in en:
            if name == "":
                name = n
            else:
                name += ' '+ n
        for n in initials.get('N'):
            n = n.replace('.', '')
            name += ' ' + n + partition

        for a in la:
            if lastname == "":
                lastname = a
            else:
                lastname += partition2 + a

        for a in initials.get('A'):
            a = a.replace('.', '')
            lastname += ' ' + a + partition

        list_reg.append(name + ' ' + lastname)

        for reg in list_reg:
            yield reg

    def _inversion(self, vcn, la):
        list_reg = []

        lastname = ""
        name = ""
        partition = ',?[\s]*?'
        partition2 = '[\s-]+?'
        partition3 = '\.?-?'
        partition4 = '\.?'


        for a in la:
            if lastname == "":
                lastname = a
            else:
                lastname += partition2 + a

            for n in vcn:
                if name == "":
                    name = n[0]
                else:
                    name += partition3 + n[0]

                list_reg.append(lastname+partition+name+partition4)

            name = ""


        for reg in list_reg:
            yield reg

    def _literal(self, ln, la, initials):

        list_reg = []

        partition = '[\s-]+?'
        partition2 = ',?[\s]*?'
        name = ""
        lastname = ""

        for a in la:
            if lastname == "":
                lastname = a
            else:
                lastname += partition + a

            for n in ln:
                if name == "":
                    name = n
                else:
                    name += partition2 + n

                list_reg.append(lastname)
                list_reg.append(name + partition2 + lastname)
                list_reg.append(lastname + partition2 + name)

            for n in initials.get("N"):
                name += partition + n
                list_reg.append(name + partition2 + lastname)
                list_reg.append(lastname + partition2 + name)
                for ia in initials.get("A"):
                    lastname += partition + ia
                    list_reg.append(name + partition2 + lastname)
                    list_reg.append(lastname + partition2 + name)
            name = ""

        for reg in list_reg:
            yield reg

    def _extra_element(self, ln, la):

        list_reg = []

        name = ""
        lastname = ""

        partition = '[A-Z][a-z]+'
        partition2 = '[\s]+'

        for a in la:
            if lastname == "":
                lastname = a
            else:
                lastname += partition2 + a

        for n in ln:
            if name == "":
                name = n
            else:
                name += partition2 + n

            list_reg.append(n + partition2 + partition + partition2 + lastname)

        list_reg.append(name + partition2 + partition + partition2 + lastname)

        for reg in list_reg:
            yield reg

    def _name_variations(self):
        variations = {}
        names = []
        surnames = []
        initials = {"N": [], "A": []}

        for tree in self.tree:
            print(tree)
            for person in tree:
                if person.label() == 'N':
                    for node in person.subtrees(lambda k: k.height() == 2):
                        if node.label() == "AA":
                            names.append(
                                node.leaves()[0])
                        elif node.label() == 'I':
                            (initials.get('N')).append(
                                node.leaves()[0])
                        elif node.label() == 'AD':
                            tmp = node.leaves()[0]
                            names.append(
                                tmp.split(' ')[1]
                            )
                        elif node.label() == 'AG':
                            tmp = node.leaves()[0]
                            for t in tmp.split('-'):
                                names.append(t)

                elif person.label() == 'A':
                    for node in person.subtrees(lambda k: k.height() == 2):
                        if node.label() == 'AA':
                            surnames.append(
                                node.leaves()[0])
                        elif node.label() == 'I':
                            (initials.get('A')).append(
                                node.leaves()[0])
                        elif node.label() == 'AD':
                            tmp = node.leaves()[0]
                            surnames.append(
                                tmp.split(' ')[1]
                            )
                        elif node.label() == 'AG':
                            tmp = node.leaves()[0]
                            for t in tmp.split('-'):
                                surnames.append(t)
            break

        # --- Debugging ---
        print(names)
        print(surnames)
        print(initials)

        if surnames.__len__() > 0:
            for reg in self._literal(names, surnames, initials):
                self._add_variation(reg, variations, 'L')

            for reg in self._compression(names, surnames):
                self._add_variation(reg, variations, 'C')

            for reg in self._expansion(names, surnames, initials):
                self._add_variation(reg, variations, 'E')

            for reg in self._extra_element(names, surnames):
                self._add_variation(reg, variations, 'X')

            for reg in self._inversion(names, surnames):
                self._add_variation(reg, variations, 'V')

        return variations

    def filter(self, snippet):

        snippet = Cleaner.remove_accent(Cleaner(), snippet)
        snippet = Cleaner.clean_reserved_xml(Cleaner(), snippet)

        vect = np.zeros(self.list_regex.__len__())

        for item in self.list_regex.items():
            label = item[0]
            for pattern in item[1]:
                regex = re.compile(pattern)

                if regex.search(snippet):
                    vect[self.dic_vect.get(label)] = 1

        return vect


class Cleaner:

    def __init__(self):
        self._re_a = re.compile(u'[áâàä]')
        self._re_e = re.compile(u'[éèêëě]')
        self._re_i = re.compile(u'[íïîì]')
        self._re_o = re.compile(u'[óòôöø]')
        self._re_u = re.compile(u'[úùüû]')
        self._re_n = re.compile(u'[ñ]')
        self._re_c = re.compile(u'[ç]')
        self._re_y = re.compile(u'[ỳýÿŷ]')
        self._re_beta = re.compile(u'[ß]')
        self._re_A = re.compile(u'[ÁÀÄÂÅ]')
        self._re_E = re.compile(u'[ÉÈÊË]')
        self._re_I = re.compile(u'[ÍÌÏÎ]')
        self._re_O = re.compile(u'[ÓÒÔÖØ]')
        self._re_U = re.compile(u'[ÚÙÛÜ]')
        self._re_N = re.compile(u'[Ñ]')
        self._re_C = re.compile(u'[Ç]')
        self._re_S = re.compile(u'[Š]')

    def remove_accent(self, line_u):

        line_u = self._re_a.subn('a', line_u)[0]
        line_u = self._re_e.subn('e', line_u)[0]
        line_u = self._re_i.subn('i', line_u)[0]
        line_u = self._re_o.subn('o', line_u)[0]
        line_u = self._re_u.subn('u', line_u)[0]
        line_u = self._re_n.subn('n', line_u)[0]
        line_u = self._re_c.subn('c', line_u)[0]
        line_u = self._re_y.subn('y', line_u)[0]
        line_u = self._re_beta.subn('ss', line_u)[0]
        line_u = self._re_A.subn('A', line_u)[0]
        line_u = self._re_E.subn('E', line_u)[0]
        line_u = self._re_I.subn('I', line_u)[0]
        line_u = self._re_O.subn('O', line_u)[0]
        line_u = self._re_U.subn('U', line_u)[0]
        line_u = self._re_N.subn('N', line_u)[0]
        line_u = self._re_C.subn('C', line_u)[0]
        line_u = self._re_S.subn('S', line_u)[0]

        return line_u
    
    def clean_reserved_xml(self, line):
        r = line.replace('&apos;', "'")
        r = r.replace('&lt;', "<")
        r = r.replace('&gt;', ">")
        r = r.replace('&quot;', '"')
        r = r.replace('&amp;', "&")
        return r

class Freeling:

    def __init__(self):

        # config = configparser.ConfigParser()


        # FREELING_LIB = config.get('freeling', 'lib')
        data_dir = "FreeLing/data/en/"
        data_dir_common = "FreeLing/data/common/"

        freeling.util_init_locale("default")

        self.la = freeling.lang_ident(data_dir_common + "lang_ident/ident.dat")


        opt = freeling.maco_options('en')

        # (usr, pun, dic, aff, comp, loc, nps, qty, prb)
        opt.set_data_files("", data_dir_common + "punct.dat", data_dir + "",
                                data_dir + "afixos.dat", data_dir + "compounds.dat",
                                data_dir + "locucions.dat", data_dir + "np.dat",
                                data_dir + "quantities.dat", data_dir + "probabilitats.dat")

        self.mf = freeling.maco(opt)

        # (umap, num, pun, dat, dic, aff, comp, rtk, mw, ner, qt, prb)
        # (0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0)
        self.mf.set_active_options(0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0)

        self.tk = freeling.tokenizer(data_dir + "tokenizer.dat")
        self.sp = freeling.splitter(data_dir + "splitter.dat")

        self.sid = self.sp.open_session()

        self.tg = freeling.hmm_tagger(data_dir + "tagger.dat", True, 2)
        self.sen = freeling.senses(data_dir + "senses.dat")

        self.parser = freeling.chart_parser(data_dir + "chuncker/grammar-chunk.dat")

        self.dep = freeling.dep_txala(data_dir + "/dep_txala/dependences.dat",
                                 self.parser.get_start_symbol())

    def test(self, cad):
        l = self.tk.tokenize(cad)

        self.ls = self.sp.split(
            self.sid, l, False
        )

        self.ls = self.mf.analyze(self.ls)
        self.ls = self.tg.analyze(self.ls)
        self.ls = self.sen.analyze(self.ls)
        self.ls = self.parser.analyze(self.ls)
        self.ls = self.dep.analyze(self.ls)

        for s in self.ls:
            ws = s.get_words()
            for w in ws:
                print(w.get_form() + " " + w.get_lemma() + " " + w.get_tag() + " " + w.get_senses_string())
            print("")

            tr = s.get_parse_tree()
            print(tr,0)
        self.sp.close_session(self.sid);