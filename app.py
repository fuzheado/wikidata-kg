from flask import Flask, request, redirect, render_template
from flask_bootstrap import Bootstrap
import os
import yaml
import urllib.parse

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

kg_sparql_template_in_url = 'https://query.wikidata.org/embed.html#%23defaultView%3AGraph%0ASELECT%20%3Fitem1%20' \
                            '%3Fimage%20%3Fitem1Label%20%3Fitem2%20%3Fimage2%20%3Fitem2Label%20%3FedgeLabel%20WHERE' \
                            '%20%7B%0AVALUES%20%3Fitem1%20%7B{}%7D%0AVALUES%20%3Fitem2%20%7B{' \
                            '}%7D%0A%3Fitem1%20%3Fprop%20%3Fitem2.%0A%3Fedge%20%3Fdummy%20%3Fprop%20%3B%20rdf%3Atype' \
                            '%20wikibase%3AProperty%0AOPTIONAL%20%7B%3Fitem1%20wdt%3AP18%20%3Fimage%7D%0AOPTIONAL%20' \
                            '%7B%3Fitem2%20wdt%3AP18%20%3Fimage2%7D%0ASERVICE%20wikibase%3Alabel%20%7B%20bd' \
                            '%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cen%22.%20%7D%0A%7D '


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/form')
def form():
    return render_template('form.html')


def redirect_to_kg(items):
    # params = '{} request content: {}'.format(request.method, items)
    # sparql_request = kg_sparql_template.format(items, items)
    # TODO Extract each line as a different item into a dict
    # TODO Handle different types of items in textarea - morph to wd:Q123 format
    # TODO handle raw Q numbers - Q1234
    # TODO handle article names with lang - en:Cambridge
    # TODO handle article names w/o lang, but default lang - Cambridge
    quoted_items = urllib.parse.quote(items.replace('\n', ' ').replace('\r', ''))
    # Use redirect to send folks to Wikidata Query
    return redirect(kg_sparql_template_in_url.format(quoted_items, quoted_items))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    textarea_content = None
    if request.method == "POST":
        textarea_content = request.form['items']
    elif request.method == "GET":
        if request.args.get('items'):
            textarea_content = request.args['items']
    else:
        return 'No valid GET or POST request'

    return redirect_to_kg(textarea_content)


if __name__ == '__main__':
    app.run()
