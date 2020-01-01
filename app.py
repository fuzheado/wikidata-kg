from flask import Flask, request, redirect, render_template
from flask_bootstrap import Bootstrap
import os
import yaml
import urllib.parse
import requests
import qutils

app = Flask(__name__)

bootstrap = Bootstrap(app)

# Load configuration from YAML file
__dir__ = os.path.dirname(__file__)
app.config.update(
    yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

kg_sparql_template = '''
#defaultView:Graph
SELECT ?item1 ?image ?item1Label ?item2 ?image2 ?item2Label ?edgeLabel WHERE {{
  VALUES ?item1 {{ {} }}
  VALUES ?item2 {{ {} }}
  ?item1 ?prop ?item2.
  ?edge ?dummy ?prop ; rdf:type wikibase:Property
  OPTIONAL {{?item1 wdt:P18 ?image}}
  OPTIONAL {{?item2 wdt:P18 ?image2}}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
'''

# URL of a SPARQL query to find the knowledge graph links
#   two {} placeholders exist to substitute in the list of wd:Q123 like items
kg_sparql_template_in_url = 'https://query.wikidata.org/embed.html#%23defaultView%3AGraph%0ASELECT%20%3Fitem1%20' \
                            '%3Fimage%20%3Fitem1Label%20%3Fitem2%20%3Fimage2%20%3Fitem2Label%20%3FedgeLabel%20WHERE' \
                            '%20%7B%0AVALUES%20%3Fitem1%20%7B{}%7D%0AVALUES%20%3Fitem2%20%7B{' \
                            '}%7D%0A%3Fitem1%20%3Fprop%20%3Fitem2.%0A{}%3Fedge%20%3Fdummy%20%3Fprop%20%3B%20rdf%3Atype' \
                            '%20wikibase%3AProperty%0AOPTIONAL%20%7B%3Fitem1%20wdt%3AP18%20%3Fimage%7D%0AOPTIONAL%20' \
                            '%7B%3Fitem2%20wdt%3AP18%20%3Fimage2%7D%0ASERVICE%20wikibase%3Alabel%20%7B%20bd' \
                            '%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D '

# MINUS { ?item1 {} ?item2 } w/newline
minus_p_template = r'MINUS%20%7B%20%3Fitem1%20{}%20%3Fitem2%20%7D%0A'


@app.route('/')
def form():
    return render_template('form.html')
    # TODO - pass in links to common tools - Wikidata Query, Pagepile, Petscan


def create_kg_url(q_items_list: list, p_exclusion_items_list: list = None):
    """
    Create Wikidata Query - Knowledge Graph URL
    """
    quoted_items = urllib.parse.quote(' '.join(q_items_list))

    # Format the P exclusions list items using the template, then into a string
    p_exclusion_items = ''.join([''.join(minus_p_template.format(x)) for x in p_exclusion_items_list])

    target_url = kg_sparql_template_in_url.format(quoted_items, quoted_items, p_exclusion_items)

    # Return URL for Wikidata Query
    return target_url


def redirect_to_kg(q_items_list: list, p_exclusion_items_list: list = None):
    """
    Redirect items to Wikidata Query site
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
        items_content = request.form['items']
        exclusions_content = request.form['exclusions']
        p_exclusions_content = request.form['property_exclusions']
        action = request.form['action']
    elif request.method == "GET":
        if request.args.get('items'):
            items_content = request.args['items']
            exclusions_content = request.args['exclusions']
            p_exclusions_content = request.args['property_exclusions']
            action = request.args['action']
    else:
        return 'No valid GET or POST request'

    # Convert/expand items
    q_items_list = qutils.item_string_to_wdq_list(items_content)

    # Convert/expand exclusions
    exclusions_list = qutils.item_string_to_wdq_list(exclusions_content)
    p_exclusions_list = qutils.item_string_to_p_list(p_exclusions_content)

    final_list = [x for x in q_items_list if x not in exclusions_list]

    if action == 'process':
        return redirect_to_kg(final_list, p_exclusions_list)
    elif action == 'print':
        return 'Request URL: {} \nKG URL: {}\nURL: {}'.format(create_kg_url(final_list, p_exclusions_list),
                                                             request.query_string,
                                                              request.url
                                                              )
    else:
        return 'No valid GET or POST request'


if __name__ == '__main__':
    app.run()
