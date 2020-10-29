from flask import Flask, request, redirect, render_template
from flask_bootstrap import Bootstrap
import os
import yaml
import urllib.parse
# import requests
import qutils  # Custom library

app = Flask(__name__)

bootstrap = Bootstrap(app)

# Load configuration from YAML file
__dir__ = os.path.dirname(__file__)
app.config.update(
    yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

# URL of a SPARQL query to find the knowledge graph links
#   three {} placeholders exist to substitute in the list of wd:Q123 like items
#   - two of these are for the list of items to graph
#   - the other is for the MINUS statements describing properties to exclude
kg_sparql_template_in_url = \
    'https://query.wikidata.org/embed.html#%23defaultView%3AGraph%0ASELECT%20%3Fitem1%20' \
    '%3Fimage%20%3Fitem1Label%20%3Fitem2%20%3Fimage2%20%3Fitem2Label%20%3FedgeLabel%20WHERE' \
    '%20%7B%0AVALUES%20%3Fitem1%20%7B{}%7D%0AVALUES%20%3Fitem2%20%7B{' \
    '}%7D%0A%3Fitem1%20%3Fprop%20%3Fitem2.%0A{}%3Fedge%20%3Fdummy%20%3Fprop%20%3B%20rdf%3Atype' \
    '%20wikibase%3AProperty%0AOPTIONAL%20%7B%3Fitem1%20wdt%3AP18%20%3Fimage%7D%0AOPTIONAL%20' \
    '%7B%3Fitem2%20wdt%3AP18%20%3Fimage2%7D%0ASERVICE%20wikibase%3Alabel%20%7B%20bd' \
    '%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D'

# MINUS { ?item1 {} ?item2 } w/newline
minus_p_template = r'MINUS%20%7B%20%3Fitem1%20{}%20%3Fitem2%20%7D%0A'

# URL of SPARQL query to show works of a given creator (P170), and what is depicted in those works (P180)
kg_creator_sparql_template_in_url = \
    'https://query.wikidata.org/embed.html#%23%20Artists%20and%20their%20works%20depictions%0A' \
    '%23defaultView%3AGraph%0ASELECT%20%3Fitem1%20%3Fimage1%20%3Fitem1Label%20%3Fitem2%20%3Fimage2%20' \
    '%3Fitem2Label%20%3Fsize%20%3Frgb%20%0AWHERE%20%0A%7B%0A%20VALUES%20%3Fcreator%20%7B%20wd%3A{}%20%7D%0A' \
    '%20%7B%20%23%20Get%20works%20and%20instances%0A%20%20VALUES%20%3Frgb%20%7B%20"FFBD33"%20%7D%0A%20%20' \
    'VALUES%20%3Fsize%20%7B%202%20%7D%0A%20%20%3Fitem1%20wdt%3AP170%20%3Fcreator%20.%0A%20%20%3Fitem1%20' \
    'wdt%3AP31%20%3Fitem2%20.%0A%20%20OPTIONAL%20%7B%20%3Fitem1%20wdt%3AP18%20%3Fimage1.%20%7D%0A%20%7D%20%0A%20' \
    'UNION%0A%20%7B%20%23%20Depictions%0A%20%20VALUES%20%3Frgb%20%7B%20"fff033"%20%7D%0A%20%20' \
    'VALUES%20%3Fsize%20%7B%201%20%7D%0A%20%20%3Fitem1%20wdt%3AP170%20%3Fcreator%20.%0A%20%20%3Fitem1%20' \
    'wdt%3AP180%20%3Fitem2%20.%0A%20%20OPTIONAL%20%7B%20%3Fitem1%20wdt%3AP18%20%3Fimage1.%20%7D%0A%20%7D%0A%20' \
    'SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20"%5B' \
    'AUTO_LANGUAGE%5D%2Cen".%20%7D%0A%7D'

# URL of SPARQL
kg_filmmaker_sparql_template_in_url = \
    'https://query.wikidata.org/embed.html#' \
    '%23%20Film%2FTV%20creator%2Fproducer%2Fdirector%20and%20the%20cast%20members%20they%20have%20worked%20with%0A' \
    '%23defaultView%3AGraph%0ASELECT%20%3Fitem1%20%3Fimage1%20%3Fitem1Label%20%3Fitem2%20%3Fimage2%20' \
    '%3Fitem2Label%20%3FedgeLabel%20%3Fsize%20%3Frgb%20%0AWHERE%20%0A%7B%0A%20%20%20%20VALUES%20%3Fcreator%20' \
    '%7B%20wd%3A{}%20%7D%0A%20%20%20%20%7B%20%23%20Get%20works%20and%20instances%0A%20%20%20%20%20%20%20%20' \
    'VALUES%20%3Frgb%20%7B%20"FFBD33"%20%7D%0A%20%20%20%20%20%20%20%20VALUES%20%3Fsize%20%7B%202%20%7D%0A' \
    '%20%20%20%20%20%20%20%20%3Fitem1%20wdt%3AP170%20%7C%20wdt%3AP57%20%7C%20wdt%3AP162%20%3Fcreator%20.%0A' \
    '%20%20%20%20%20%20%20%20%3Fitem1%20wdt%3AP31%20%3Fitem2%20.%0A%20%20%20%20%20%20%20%20OPTIONAL' \
    '%20%7B%20%3Fitem1%20wdt%3AP18%20%3Fimage1.%20%7D%0A%20%20%20%20%20%20%20%20%23%20OPTIONAL%20%7B' \
    '%20%3Fitem2%20wdt%3AP18%20%3Fimage2.%20%7D%0A%20%20%20%20%7D%20%0A%20%20%20%20UNION%0A%20%20%20%20%7B' \
    '%20%23%20Actors%0A%20%20%20%20%20%20%20%20VALUES%20%3Frgb%20%7B%20"fff033"%20%7D%0A%20%20%20%20%20%20%20%20' \
    'VALUES%20%3Fsize%20%7B%201%20%7D%0A%20%20%20%20%20%20%20%20%3Fitem1%20wdt%3AP170%20%7C%20wdt%3AP57%20%7C%20' \
    'wdt%3AP162%20%3Fcreator%20.%0A%20%20%20%20%20%20%20%20%3Fitem1%20wdt%3AP161%20%3Fitem2%20.%0A%20%20%20%20' \
    '%20%20%20%20OPTIONAL%20%7B%20%3Fitem1%20wdt%3AP18%20%3Fimage1.%20%7D%0A%20%20%20%20%20%20%20%20%23%20OPTIONAL' \
    '%20%7B%20%3Fitem2%20wdt%3AP18%20%3Fimage2.%20%7D%0A%20%20%20%20%7D%0A%20%20%20%20SERVICE%20wikibase%3Alabel%20' \
    '%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20"%5BAUTO_LANGUAGE%5D%2Cen".%20%7D%0A%7D'


@app.route('/')
def form():
    return render_template('form.html')
    # TODO - show links to common tools - Wikidata Query, Pagepile, Petscan


def create_kg_url(q_items_list: list, p_exclusion_items_list: list = None) -> str:
    """
    Create Wikidata Query - Knowledge Graph URL

    Sample q_items_list: ['wd:Q22676', 'wd:Q1057303', 'wd:Q805212']
    Sample p_exclusion_items_list - ['wdt:P123','wd:P456','wd:P789']
    """
    # Splice together list of wd:Q123 items and URL encode them into a string
    if q_items_list:
        quoted_items = urllib.parse.quote(' '.join(q_items_list))
    else:
        return ''

    # Format the P exclusions list items using the template, then put into a string
    if p_exclusion_items_list:
        p_exclusion_items = ''.join([''.join(minus_p_template.format(x)) for x in p_exclusion_items_list])
    else:
        p_exclusion_items = ''

    # Form a URL for query.wikidata.org
    target_url = kg_sparql_template_in_url.format(quoted_items, quoted_items, p_exclusion_items)

    # Return URL for Wikidata Query
    return target_url


def redirect_to_kg(q_items_list: list, p_exclusion_items_list: list = None):
    """
    Redirect user to Wikidata Query site to execute the KG SPARQL
    """
    # Redirect user's browser to Wikidata Query
    return redirect(create_kg_url(q_items_list, p_exclusion_items_list))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    items_content = None
    exclusions_content = None
    p_exclusions_content = None
    action = "process"  # Default: process the graph

    if request.method == "POST":
        if request.form.get('items'):
            items_content = request.form['items']
            exclusions_content = request.form['exclusions']
            p_exclusions_content = request.form['property_exclusions']
            action = request.form['action']
        else:
            return 'POST request had no valid request.form content'
    elif request.method == "GET":
        if request.args.get('items'):
            items_content = request.args['items']
            exclusions_content = request.args['exclusions']
            p_exclusions_content = request.args['property_exclusions']
            action = request.args['action']
        else:
            return 'GET request had no valid request.args content'
    else:
        return 'No valid GET or POST request'

    # Convert/expand items from interface into Wikidata Q items list
    q_items_list = qutils.item_string_to_wdq_list(items_content)

    # Convert/expand exclusions for Wikidata Q and P items
    exclusions_list = qutils.item_string_to_wdq_list(exclusions_content)
    p_exclusions_list = qutils.item_string_to_p_list(p_exclusions_content)

    # Create final Wikidata Q items list, removing exclusions
    final_list = [x for x in q_items_list if x not in exclusions_list]

    # TODO - provide a way to prune/trim specific triples (nonurgent)

    if action == 'process':
        return redirect_to_kg(final_list, p_exclusions_list)
    elif action == 'print':
        # Create a page with links to different URLs for later use
        # Refactor URL that invoked this page, by replacing print with process
        local_url = request.url.replace("action=print", "action=process")
        # Return URL will link directly to Wikidata Query with SPARQL code
        kg_url = create_kg_url(final_list, p_exclusions_list)

        return render_template('listurls.html', kg_url=kg_url, local_url=local_url)
    elif action == 'fillform':
        # TODO take parameters passed in on the URL and populate the textareas
        return None
    else:
        return 'No valid GET or POST request'


#
# Creator
#

@app.route('/creator')
def creator_form():
    return render_template('creator-form.html')


@app.route('/submit-creator', methods=['GET', 'POST'])
def submit_creator():
    items_content = None
    action = "process"  # Default: process the graph

    if request.method == "POST":
        if request.form.get('items'):
            items_content = request.form['items']
            action = request.form['action']
        else:
            return 'POST request had no valid request.form content'
    elif request.method == "GET":
        if request.args.get('items'):
            items_content = request.args['items']
            action = request.args['action']
        else:
            return 'GET request had no valid request.args content'
    else:
        return 'No valid GET or POST request'

    # Convert/expand items from interface into Wikidata Q items list
    # q_items_list = qutils.item_string_to_wdq_list(items_content)
    print(items_content)
    # TODO - check items to make sure there is but one Q number

    if action == 'process':
        return redirect("/creator/" + items_content)
    else:
        return 'No valid GET or POST request'


@app.route('/creator/<string:qid>', methods=['GET'])
def creator_kg(qid):
    # TODO - some sanity checking of qid
    # assert isinstance(qid, object)
    return redirect(kg_creator_sparql_template_in_url.format(qid))


#
# Film maker
#

@app.route('/filmmaker')
def filmmaker_form():
    return render_template('filmmaker-form.html')


@app.route('/submit-filmmaker', methods=['GET', 'POST'])
def submit_filmmaker():
    items_content = None
    action = "process"  # Default: process the graph

    if request.method == "POST":
        if request.form.get('items'):
            items_content = request.form['items']
            action = request.form['action']
        else:
            return 'POST request had no valid request.form content'
    elif request.method == "GET":
        if request.args.get('items'):
            items_content = request.args['items']
            action = request.args['action']
        else:
            return 'GET request had no valid request.args content'
    else:
        return 'No valid GET or POST request'

    # Convert/expand items from interface into Wikidata Q items list
    # q_items_list = qutils.item_string_to_wdq_list(items_content)
    print(items_content)
    # TODO - check items to make sure there is but one Q number

    if action == 'process':
        return redirect("/filmmaker/" + items_content)
    else:
        return 'No valid GET or POST request'


@app.route('/filmmaker/<string:qid>', methods=['GET'])
def filmmaker_kg(qid):
    # TODO - some sanity checking of qid
    # assert isinstance(qid, object)
    return redirect(kg_filmmaker_sparql_template_in_url.format(qid))


if __name__ == '__main__':
    app.run()
