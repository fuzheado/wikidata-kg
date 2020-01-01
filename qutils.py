import requests
import re

"""
Utility functions to help with Wikidata Q items, Pagepiles and Wikipedia
"""

pagepile_api_url = 'https://tools.wmflabs.org/pagepile/api.php'


def pagepile_id_to_qid_list(pagepile_id: int) -> list:
    """Convert a wiki pagepile ID (int) to a list of Wikidata Q items
    12345 -> ['Q123','Q456','Q789']

    Currently only works only for Wikidata-specific pagepiles
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

        request_url = 'https://' + lang + '.wikipedia.org/w/api.php'
        r = requests.get(request_url, params)
        r.raise_for_status()
        data = r.json()
    except ValueError:
        print('Failed to get result')
        return None

    if 'query' not in data:
        raise ValueError("No query content in given data")
    if 'pages' not in data['query']:
        raise ValueError("No pages in given data")

    if 'missing' in data['query']['pages'][0]:
        if data['query']['pages'][0]['missing'] is True:
            print('wikititle_to_qid: API returned missing for '+lang+':'+title)
            return None

    if 'pageprops' in data['query']['pages'][0]:
        if 'wikibase_item' in data['query']['pages'][0]['pageprops']:
            return data['query']['pages'][0]['pageprops']['wikibase_item']

    return None


def item_string_to_wdq_list(items: str) -> list:
    """Take a newline separated list of possible discrete items and make a list of Wikidata Q numbers
    wd:Q123
    Q123
    pagepile:12345
    en:Kygo

    Return a list of Q items in wd:Q123 format, ready to concatenate together for use in SPARQL
    ['wd:Q123','wd:Q456','wd:Q789']

    This function will also de-duplicate the list, so order will NOT be preserved in any way
    """

    items_list = items.splitlines()  # String usually from HTML <textarea>, lots of whitespace
    items_list = list(filter(None, [x.strip() for x in items_list]))  # Strip whitespace, empty items

    for n, item in enumerate(items_list):

        # wd:Q123 - wd prefix on valid q number
        if re.match(r'^wd:[Qq]\d+$', item) is not None:
            continue

        # Q123 - Valid Q number, no wd
        elif re.match(r'^[Qq]\d+$', item) is not None:
            items_list[n] = 'wd:' + item

        # 123 - Valid number, no Q or wd, treat as Wikidata qid
        elif re.match(r'^\d+$', item) is not None:
            items_list[n] = 'wd:Q' + item

        # pagepile:123 - expand this via API to Q numbers
        elif re.match(r'^pagepile:\d+$', item):
            m = re.search(r'^pagepile:(\d+)$', item)  # Extract number
            if m:
                pile_id = m.group(1)
                # Retrieve Q items from Pagepile API
                # Currently only works on Wikidata Pagepile
                pile_list = pagepile_id_to_qid_list(pile_id)
                if pile_list:
                    items_list.pop(n)  # Remove Pagepile ID from list, prep for insertion
                    # Use list slicer to insert Pagepile-expanded Wikidata items
                    # https://stackoverflow.com/questions/3748063/what-is-the-syntax-to-insert-one-list-into-another-list-in-python
                    items_list[n:n] = ['wd:' + x for x in pile_list]
            else:
                items_list.pop(n)  # Silently fail, remove the ID from list

        # en:Kygo
        elif re.match(r'^[a-z]+:.+$', item) is not None:
            m = re.match(r"^(?P<lang>[-a-z]+):(?P<title>.+)$", item)
            wiki_dict = m.groupdict()  # Extract regex matches into dict
            qid = wikititle_to_qid(wiki_dict['lang'], wiki_dict['title'])
            if qid is not None:
                items_list[n] = 'wd:' + qid  # Replace en:Foobar with wd:Q860
            else:
                # Silently fail, remove the entry from list
                print ('Before: '+str(items_list))
                try:
                    del items_list[n]
                except IndexError:
                    print("API lookup: index Out of Range")
                print ('After: '+str(items_list))

        # No patterns match at all, silently get rid of bogus entry
        else:
            items_list.pop(n)  # Silently fail, remove the ID from list

    # return items_list
    # Assuming order does not matter, de-duplicate by turning into a set
    return list(set(items_list))


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

    if items.strip() is None:
        return None

    items_list = items.splitlines()  # String usually from HTML <textarea>, lots of whitespace
    items_list = list(filter(None, [x.strip() for x in items_list]))  # Strip whitespace, empty items

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
    """
    print('** Testing valid pagepile id for Wikidata: ' + str(27684))
    print(pagepile_id_to_qid_list(27684))
    print('** Testing invalid pagepile id for Wikidata: ' + str(27680))
    print(pagepile_id_to_qid_list(27680))
    """

    items = """
    wd:Q123
    Q456
    pagepile:27684
    Q42
    1234
    en:Kygo
    en:Barack Obama
    en:Columbia University
    en:The White House
    """
    items = """
    pagepile:27700
    """
    # print('** Testing items: ')
    # print(item_string_to_wdq_list(items))
    # print(pagepile_id_to_qid_list(27700))

    items = """
    wdt:P170
    P31
    3634
    """
    print(item_string_to_p_list(items))

    p_exclusion_items_list = item_string_to_p_list(items)
    minus_p_template = r'MINUS {{ ?item1 {} ?item2 }}'
    # [print(minus_p_template.format(x)) for x in item_string_to_p_list(items)]
    # p_exclusion_items=str(None)
    # [foo.join(minus_p_template.format(x)) for x in item_string_to_p_list(items)]

    p_exclusion_items = '\n'.join([''.join(minus_p_template.format(x)) for x in p_exclusion_items_list])

    # print ('p_exclusion_items: '+str(p_exclusion_items))

    # print(minus_p_template)
    # print(wikititle_to_qid("en", "Ballet flat"))
    # print(wikititle_to_qid("en", "Stiletto (shoe)"))

    test_items='''\
en:Stiletto (foobar) 
en:Shoe 
en:High-heel shoe
en:Ballet flat'''
    item_string_to_wdq_list(test_items)