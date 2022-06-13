import json
import os
import pathlib
import sys
from collections import defaultdict
import random
import networkx as nx
import matplotlib.pyplot as plt
import re

from check import check

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

FILENAME                    = "template.json"
RESOURCES_KEY               = "resources"
NAME_KEY                    = "name"
ID_KEY                      = "id"
TYPE_KEY                    = "type"
DEPENDS_ON_KEY              = "dependsOn"
DEFAULT_OUTPUT_EXTENSION    = "png"

def to_safe_fname(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in { ' ', '+', '-' } ]).rstrip()

def filename_to_outputname(filename, output_extension = None):
    return to_safe_fname(f"{pathlib.Path(filename)}")

def get_random_color():
    return "#"+''.join([random.choice('0123456789ABCDEF') for _ in range(6)])

def parse_resource_name(raw_dependancy):
    raw_dependancy = re.sub(".*providers/", "", raw_dependancy)
    return raw_dependancy               \
        .replace("[", "")               \
        .replace("]", "")               \
        .replace("', ", "/")            \
        .replace("'), ", "/")           \
        .replace("'", "")               \
        .replace("(", "")               \
        .replace(")", "")               \
        .replace("\\", "")              \
        .replace("\"", "")              \
        .replace("resourceId", "")      \
        .replace("parameters", "")      \
        .replace("concat", "")          \
        .replace("'/", "'")             \
        .replace(", ", "\\")            \
        .replace("\\", "/")             \
        .replace("//", "/")

def translate_dictionary_to_graph(d, n):
    G = nx.DiGraph()
    G.add_nodes_from(n)
    for x, l in d.items():
        for y in l:
            G.add_edge(x, y)
    return G

def filter_by_type(G, types_filter):
    if not types_filter:
        return
    for x in [x for x in G]:
        for t in types_filter:
            if t in x:
                G.remove_node(x)
                break

def get_error_node(type, tuples):
    for t in tuples:
        if type == t[0]:
            return t
    return None

def create_color_map(G, resource_to_type, errorNodes, labels):
    color_map = []
    type_color = defaultdict()
    for resource_name in G:
        resource_type = resource_to_type[resource_name]
        if resource_type not in type_color:
            type_color[resource_type] = get_random_color()

        errorNode = get_error_node(resource_name, errorNodes)
        if errorNode != None:
            color_map.append('red')
            labels[resource_name] = f'\n\nError: {errorNode[1]}'
        else:
            color_map.append(type_color[resource_type])
    return color_map


def generate_labels(G, error_nodes):
    labeldict = {}
    labeldict["Node1"] = "shopkeeper"
    labeldict["Node2"] = "angry man with parrot"
    return labeldict

def draw_graph_to_file(G, color_map, filename, labels, output_extension = None):
    plt.clf()
    plt.figure(5, figsize=(30, 30))
    pos = nx.fruchterman_reingold_layout(G)
    nx.draw_networkx_nodes(G, pos, cmap=plt.get_cmap('jet'), node_size=500)
    nx.draw_networkx_labels(G, pos)
    nx.draw(G, pos=pos, node_size=[v * 1000 for v in dict(G.degree).values()], node_color=color_map, labels=labels, with_labels = True)
    # Save to file
    outputname = filename_to_outputname(filename, output_extension=output_extension)
    plt.savefig(fname=outputname)

def handle_graph(d, n, types_filter, resource_to_type, filename, output_extension = None, validator = None):
    G = translate_dictionary_to_graph(d, n)
    if validator:
        error_nodes = validator(G, resource_to_type)
        is_valid = len(error_nodes) == 0
        print(f"{bcolors.OKGREEN if is_valid else bcolors.FAIL} {filename} {is_valid} {bcolors.ENDC}")
    filter_by_type(G, types_filter)
    labels = {}
    color_map = create_color_map(G, resource_to_type, error_nodes, labels)
    draw_graph_to_file(G, color_map, filename, labels, output_extension)

def extract_dependancies(raw_dependancies):
    dependencies = []
    for raw_dependency in raw_dependancies:
        dependencies.append(raw_dependency)
    return dependencies

def template_to_graph(graph_name, json_content, types_filter=None):
    resources           = json_content[RESOURCES_KEY]
    n                   = set()
    d                   = defaultdict(list)
    resource_to_type    = defaultdict()
    id_to_name          = defaultdict()
    has_primary_resource= False
    for resource in resources:
        resource_type                       = resource[TYPE_KEY]
        resource_name                       = f'{resource_type}/{parse_resource_name(resource[NAME_KEY])}'
        n.add(resource_name)
        if ID_KEY in resource:
            id_to_name[resource[ID_KEY]]    = resource_name
        resource_to_type[resource_name]     = resource_type
        # If primary resource
        if DEPENDS_ON_KEY not in resource:
            has_primary_resource = True
            continue
        # Add resource dependencies
        for depends_on in extract_dependancies(resource[DEPENDS_ON_KEY]):
            depends_on_name = id_to_name[depends_on] if depends_on in id_to_name else parse_resource_name(depends_on)
            d[resource_name].append(depends_on_name)
    # Validate primary resource
    if not has_primary_resource:
        print(f"{bcolors.FAIL} {graph_name} Has no primary resource (without incoming edges) {bcolors.ENDC}")
    handle_graph(d, n, types_filter, resource_to_type, graph_name, validator=check)

TYPES_FILTER = set() # set( ['Principal'] ) # set()

def json_handler(filename):
    with open(filename) as f:
        json_content    = json.load(f)
    template_to_graph(filename, json_content, TYPES_FILTER)

def csv_handler(filename):
    import csv
    with open('results.csv', newline='') as csvfile:
        for row in csv.reader(csvfile, delimiter=','):
            Timestamp, RAID = row[0], row[1]
            graph_name = f'{Timestamp}+{RAID}'
            json_content = json.loads(row[2])
            template_to_graph(graph_name, json_content, types_filter=TYPES_FILTER)

type_to_handler = \
    {
        ".json"  : json_handler,
        ".csv"   : csv_handler,
    }

def classify_file_to_type(filename):
    return os.path.splitext(filename)[1]

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else FILENAME
    type_handler = type_to_handler[classify_file_to_type(filename)]
    type_handler(filename)
