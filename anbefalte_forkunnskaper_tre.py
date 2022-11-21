import requests
from bs4 import BeautifulSoup
import threading
from tqdm import tqdm
import time
import sys
import os
import numpy as np
import pickle
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import webbrowser
import re


class EmneListe(list):
    def __str__(self):
        return f"{[emne.kode for emne in self]}"


class ThreadManager:
    def __init__(self, thread_count):
        self.alive = [True] * thread_count

    def end(self, i):
        self.alive[i] = False


class Emne:
    Tilbud = {}
    nivåmap = {"0": 0, "1": 0, "2": 1, "3": 2, "4": 3, "5": 3, "6": 3, "7": 4, "8": 4, "9": 4}

    def __init__(self, kode, url, navn):
        if kode not in Emne.Tilbud.keys():
            self.kode = kode
            self.url = url
            self.navn = navn
            self.anb_fork = EmneListe()
            self.deps = []
            self.fork = 0
            try:
                self.nivå = Emne.nivåmap[str(re.findall(r"\d+", self.kode)[0])[0]]
            except:
                print(f"Nivåbestemmelse for {self.kode} feilet")
                self.nivå = 0

            Emne.Tilbud[self.kode] = self

    def __repr__(self):
        return f"Emne {self.kode}"

    def __eq__(self, other):
        return self.kode == other.kode

    def dependencies(self):
        return tuple([other.kode for other in self.anb_fork])

    def dependents(self):
        return tuple([other.kode for other in self.deps])

    def forkunnskaper(self):
        page = requests.get(self.url)
        text = page.text

        st = text.find("Studiepoeng")
        if st == -1:
            st = text.find("Credits")
            opptak_søk = "Admission to the course"
            overlapp_søk = "Overlapping courses"
            oblig_søk = "Recommended previous knowledge"
        else:
            opptak_søk = "Opptak til emnet"
            overlapp_søk = "Overlappende emner"
            oblig_søk = "Anbefalte forkunnskaper"

        self.st_poeng = int(re.findall(r"\d+", text[st: st+100])[0])

        overlapp = text.rfind(overlapp_søk)
        opptak = text.rfind(opptak_søk)
        if opptak < overlapp:
            oblig = text.rfind(oblig_søk)
            cut = text[oblig: overlapp]
            soup = BeautifulSoup(cut, "html.parser")
            links = soup.find_all("a", href=True)
            for link in links:
                if "emne" not in link["href"]:
                    continue
                if "nedlagt" in link.text:
                    continue
                if "videreført" in link.text:
                    continue
                if "discontinued" in link.text:
                    continue
                if "continued" in link.text:
                    continue
                kode = link["href"].split("/")[-2]
                if kode not in Emne.Tilbud.keys():
                    if not (kode := self.nedlagt(link["href"])):
                        continue
                try:
                    emne = Emne.Tilbud[kode]
                except KeyError:
                    continue
                if emne not in self.anb_fork:
                    emne.fork += 1
                    emne.deps.append(self)
                    self.anb_fork.append(emne)

    def __hash__(self):
        return hash(self.kode)

    def nedlagt(self, link):
        try:
            page = requests.get(link)
        except requests.exceptions.MissingSchema:
            page = requests.get(uio + link)
        soup = BeautifulSoup(page.content, "html.parser")
        try:
            blue = soup.find_all("div", {
                                 "class": "vrtx-context-message-box uio-info-message blue grid-container"})[0]
        except:
            return False
        else:
            try:
                link = blue.find_all("a", href=True)[0]["href"]
                return link.split("/")[-2]
            except:
                return False

    @staticmethod
    def rist():
        keys = list(Emne.Tilbud.keys())
        np.random.shuffle(keys)
        Emne.Tilbud = {key: Emne.Tilbud[key] for key in keys}

    @staticmethod
    def finn_alle_fork(threads=1):
        print("Finner alle anbefalte forkunnskaper")
        all = list(Emne.Tilbud.values())
        np.random.shuffle(all)
        size = len(all) // threads
        rest = len(all) - size * threads
        subsets = [all[size * start: size * (start + 1)]
                   for start in range(threads)]
        if rest != 0:
            subsets[-1] += all[-rest:]

        TM = ThreadManager(threads)
        for thread in range(threads-1):
            threading.Thread(target=Emne._finn_alle_fork_thr,
                             args=(subsets[thread], TM, thread)).start()
        Emne._finn_alle_fork_thr(subsets[-1], TM, threads-1)

        while sum(TM.alive):
            time.sleep(1)
        print("\n\n\n")

    @staticmethod
    def _finn_alle_fork_thr(subset, TM, th_id):
        pbar = tqdm(range(len(subset)), desc=f"Thread {th_id}")
        for cnt in pbar:
            subset[cnt].forkunnskaper()
        TM.end(th_id)

    @staticmethod
    def drop_enslige():
        print("Dropper trivielle kurs")
        print(f"Totalt antall kurs: {len(Emne.Tilbud)}")
        tmp = {}
        for kode, emne in Emne.Tilbud.items():
            if len(emne.anb_fork) + emne.fork != 0:
                tmp[kode] = emne
        Emne.Tilbud = tmp
        print(f"Ikke-trivielle kurs: {len(Emne.Tilbud)}")

    def edges(self):
        return [(other, self) for other in self.anb_fork]


def hent_emner(sidelink, sider_sett=[]):
    print("Henter emner fra", sidelink)
    page = requests.get(sidelink)
    soup = BeautifulSoup(page.content, "html.parser")
    for a_href in soup.find_all("a", href=True):
        link = a_href["href"]
        if link[-4:] == "html" and link[0] == "/":
            emne = link.split("/")[-2]
            Emne(emne, uio + link, a_href.text)

        if "page" in link and link not in sider_sett:
            sider_sett.append(link)
            hent_emner(link, sider_sett)


def make_graph(emner):
    G = nx.DiGraph()
    G.add_nodes_from(emner.values())
    for emne in emner:
        G.add_edges_from(emner[emne].edges())
    return G


uio = "https://uio.no"
fakulteter = ["hf", "odont", "jus", "matnat",
              "sv", "teologi", "medisin", "annet"]
emneliste = lambda fakultet="matnat": f"/studier/emner/{fakultet}/"

sted = sys.argv[1]  # fakultet eller institutt
hent = True
if os.path.isfile(f"./{sted.replace('/', '_')}_emner.pkl"):
    hent = False
threads = 8  # antall tråder for innsamling av forkunnskaper.
freeze = False

if hent:
    if sted == "alle/uio":
        for fak in fakulteter:
            hent_emner(uio + emneliste(fak))
    else:
        hent_emner(uio + emneliste(sted))

    Emne.finn_alle_fork(threads)

    with open(f"./{sted.replace('/', '_')}_emner.pkl", "wb") as f:
        pickle.dump(Emne.Tilbud, f)

else:
    with open(f"./{sted.replace('/', '_')}_emner.pkl", "rb") as f:
        Emne.Tilbud = pickle.load(f)

Emne.drop_enslige()
Emne.rist()
# for emne in Emne.Tilbud.values():
#     print(f"{emne.kode:<12} {emne.nivå}: Dependencies: {len(emne.anb_fork):<3}. Dependents: {len(emne.deps):<3}")

graf = make_graph(Emne.Tilbud)
print(graf)
attrs = {emne: {"Navn": emne.navn, "Studiepoeng": emne.st_poeng}
         for emne in Emne.Tilbud.values()}
nx.set_node_attributes(graf, attrs)

shells = []
for i in range(5):
    shells.append([])
for node in graf.nodes:
    shells[node.nivå].append(node)

fig, ax = plt.subplots()
pos = nx.shell_layout(graf, nlist=shells)
pos_Emner = list(Emne.Tilbud.values())
nodes = nx.draw_networkx_nodes(graf, pos=pos, ax=ax, node_size=100)
edges = nx.draw_networkx_edges(graf, pos=pos, ax=ax)
ax.axis("off")
ax.set_title(f"Emner ved {sted.replace('/', ' ')}")


def make_edge_map(pos, edges):
    edge_map = defaultdict(lambda: [])
    for edge in edges:
        A, B = edge._posA_posB
        for node, p in pos.items():
            p = tuple(p)
            if p == A or p == B:
                edge_map[node].append(edge)
    return edge_map


edge_map = make_edge_map(pos, edges)

annot = ax.annotate("", xy=(-1, 0.9), xytext=(20, 20), textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"))
annot.set_visible(False)


def update_annot(ind):
    node = pos_Emner[ind]
    node_attr = {"Emnekode": node}
    node_attr.update(graf.nodes[node])
    text = "\n".join(f"{k}: {v}" for k, v in node_attr.items())
    annot.set_text(text)


def hide(ind):
    show_all()
    node = pos_Emner[ind]
    deps_inds = [pos_Emner.index(dep) for dep in node.deps]
    fork_inds = [pos_Emner.index(fork) for fork in node.anb_fork]

    colors = ["blue"] * len(pos)
    alphas = np.ones(len(pos)) * 0.2
    alphas[ind] = 1
    colors[ind] = "black"
    for i in deps_inds:
        alphas[i] = 1
        colors[i] = "green"
    for i in fork_inds:
        rec_deps = set(depdep(pos_Emner[i]))
        for rec in [pos_Emner.index(dep) for dep in rec_deps]:
            alphas[rec] = 0.6
            colors[rec] = "orange"
    for i in fork_inds:
        alphas[i] = 1
        colors[i] = "red"

    for edge in edges:
        if edge not in edge_map[node]:
            edge.set_alpha(0.1)

    nodes.set_alpha(alphas)
    nodes.set_color(colors)


def depdep(node):
    deps = set()
    for dep in node.anb_fork:
        deps.add(dep)
        deps |= depdep(dep)
    return deps


def show_all():
    nodes.set_alpha(1)
    [edge.set_alpha(1) for edge in edges]
    nodes.set_color("blue")


def hover(event):
    global freeze
    vis = annot.get_visible()
    if event.inaxes == ax:
        cont, ind = nodes.contains(event)
        if cont:
            update_annot(ind["ind"][0])
            if not freeze: hide(ind["ind"][0])
            annot.set_visible(True)
            fig.canvas.draw_idle()
        else:
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()
            if not freeze: show_all()


def click(event):
    if event.inaxes == ax:
        cont, ind = nodes.contains(event)
        if cont:
            webbrowser.open(pos_Emner[ind["ind"][0]].url)

def keypress(event):
    if event.key == "p":
        global freeze
        freeze = not freeze
        if not freeze: show_all()

fig.canvas.mpl_connect("motion_notify_event", hover)
fig.canvas.mpl_connect("button_press_event", click)
fig.canvas.mpl_connect("key_press_event", keypress)

plt.show()
