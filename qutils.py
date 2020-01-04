import requests
import re

"""
Utility functions to help with Wikidata Q items, Pagepiles and Wikipedia articles
by Andrew Lih (User:Fuzheado)
"""

# Location of the wiki pagepile API
pagepile_api_url = 'https://tools.wmflabs.org/pagepile/api.php'

# Location of the API for Wikipedia projects, substituting language for {}, eg. en, fr, jp
# Suggested usage: wikipedia_api_url_template.format('en')
wikipedia_api_url_template = 'https://{}.wikipedia.org/w/api.php'


def pagepile_id_to_qid_list(pagepile_id: int) -> list:
    """
    Convert a wiki pagepile ID (int) to a list of Wikidata Q items
    12345 -> ['Q123','Q456','Q789']

    Only works only for Wikidata-specific pagepiles, ie. a list of Q items
    """
    try:
        params = {'id': pagepile_id,
                  'format': 'json',
                  'action': 'get_data',
                  'doit': ''}

        r = requests.get(pagepile_api_url, params)
        r.raise_for_status()
        pile = r.json()
    except ValueError:
        # PagePile prints errors out, in invalid JSON
        print('Failed to get result')
        return []

    if r.json()['wiki'] == 'wikidatawiki':
        q_list = r.json()['pages']
        return q_list
    else:
        print('Not a Wikidata pagepile, was: ' + r.json()['wiki'])
        return []


def wikititle_to_qid(lang: str, title: str) -> str:
    """
    Converts Wikipedia lang and title to QID
    In: en:Kygo
    Out: Q16845512
    Example: https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&redirects=1&prop=pageprops&ppprop=wikibase_item&titles=Kyro
    """
    try:
        params = {'action': 'query',
                  'format': 'json',
                  'formatversion': 2,
                  'redirects': 1,
                  'prop': 'pageprops',
                  'ppprop': 'wikibase_item',
                  'titles': title}

        # Create the API request URL
        request_url = wikipedia_api_url_template.format(lang)

        # Lookup en:Foo against the Wikipedia edition
        r = requests.get(request_url, params)
        r.raise_for_status()
        data = r.json()
    except ValueError:
        print('wikititle_to_qid: Failed to get result')
        return ''

    if 'query' not in data:
        raise ValueError("wikititle_to_qid: No query content in given data")
    if 'pages' not in data['query']:
        raise ValueError("wikititle_to_qid: No pages in given data")

    if 'missing' in data['query']['pages'][0]:
        if data['query']['pages'][0]['missing'] is True:
            print('wikititle_to_qid: API returned missing for ' + lang + ':' + title)
            return ''

    if 'pageprops' in data['query']['pages'][0]:
        if 'wikibase_item' in data['query']['pages'][0]['pageprops']:
            return data['query']['pages'][0]['pageprops']['wikibase_item']

    return ''


def item_string_to_wdq_list(items: str) -> list:
    """
    Take a newline separated list of discrete items and make a list of valid Wikidata Q numbers
    wd:Q123
    Q123
    pagepile:12345
    en:Kygo

    Returns a list of Q items in wd:Q123 format, ready to concatenate together for use in SPARQL
    ['wd:Q123','wd:Q456','wd:Q789']

    This function will also de-duplicate the list, so order will NOT be preserved in any way
    """

    if not items or items.strip() is None:
        return []

    # String usually from HTML <textarea>, lots of whitespace
    items_list = items.splitlines()
    # Strip whitespace, empty items
    items_list = list(filter(None, [x.strip() for x in items_list]))
    # TODO tolerate/strip junk or comment after a Q number like:
    # wd:Q123  #foobar
    # probably make this a function so it can be called from other function too

    result_list = []
    for n, item in enumerate(items_list):

        # wd:Q123 - wd prefix on valid q number
        if re.match(r'^wd:[Qq]\d+$', item) is not None:
            result_list.append(item)

        # Q123 - Valid Q number, no wd
        elif re.match(r'^[Qq]\d+$', item) is not None:
            result_list.append('wd:' + item)

        # 123 - All numbers, no Q or wd, treat as Wikidata qid
        elif re.match(r'^\d+$', item) is not None:
            result_list.append('wd:Q' + item)

        # pagepile:123 - expand this via API to Q numbers
        elif re.match(r'^pagepile:\d+$', item):
            m = re.search(r'^pagepile:(\d+)$', item)  # Extract number
            if m:
                pile_id = m.group(1)
                # Retrieve Q items from Pagepile API
                # Currently only works on Wikidata Pagepile
                pile_list = pagepile_id_to_qid_list(pile_id)
                if pile_list:
                    result_list.append(['wd:' + x for x in pile_list])
            else:
                items_list.pop(n)  # Silently fail, remove the ID from list

        # en:Kygo - language specific article, could be redirect
        elif re.match(r'^[-a-z]+:.+$', item) is not None:
            m = re.match(r"^(?P<lang>[-a-z]+):(?P<title>.+)$", item)
            wiki_dict = m.groupdict()  # Extract regex matches into dict
            qid = wikititle_to_qid(wiki_dict['lang'], wiki_dict['title'])
            if qid:
                result_list.append('wd:' + qid)  # Replace en:Foobar with wd:Q860

        # No patterns match at all, silently skip bogus entry, continue loop

    # return items_list
    # Assuming order does not matter, de-duplicate by turning into a set
    return list(set(result_list))


def item_string_to_p_list(items: str) -> list:
    """
    Convert newline separated list of possible discrete items and make a list of Wikidata P numbers
    wdt:P123
    p:P123
    P123

    Return a list of P items in wdt:P123 format, ready to use in SPARQL
    ['wdt:P123','wd:P456','wd:P789']

    This function will also de-duplicate the list, so order will NOT be preserved in any way
    """

    if not items or items.strip() is None:
        return []

    items_list = items.splitlines()  # String usually from HTML <textarea>, lots of whitespace
    items_list = list(filter(None, [x.strip() for x in items_list]))  # Strip whitespace, empty items
    # TODO tolerate/strip junk or comment after a P number like:
    # wdt:P123  #foobar
    # probably make this a function so it can be called from other function too

    for n, item in enumerate(items_list):

        # wdt:P123 - wdt prefix on valid P number
        if re.match(r'^wdt:[Pp]\d+$', item) is not None:
            continue

        # P123 - Valid P number, no wdt
        elif re.match(r'^[Pp]\d+$', item) is not None:
            items_list[n] = 'wdt:' + item

        # 123 - Valid number, no P or wdt, treat as Wikidata property
        elif re.match(r'^\d+$', item) is not None:
            items_list[n] = 'wdt:P' + item

        # No patterns match at all, silently get rid of bogus entry
        else:
            items_list.pop(n)  # Silently fail, remove the ID from list

    # return items_list
    # Assuming order does not matter, de-duplicate by turning into a set
    return list(set(items_list))


if __name__ == '__main__':
    print('qutils: a set of functions for working Wikidata Q items and Pagepile')
    test_items = '''\
en:Stiletto (foobar) 
en:Shoe 
en:High-heel shoe
en:Ballet flat'''
    print('Example:')
    print('Raw items:')
    print(test_items)
    print('Expanded to Wikidata Q items:')
    print(item_string_to_wdq_list(test_items))
