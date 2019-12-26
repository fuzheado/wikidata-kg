import requests
import re

"""
Functions to help with Wikidata Q items, Pagepiles and Wikipedia
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
            print('wikititle_to_qid: API returned missing')
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
    print('items list: ' + str(items_list))
    items_list = list(filter(None, [x.strip() for x in items_list]))  # Strip whitespace, empty items
    print('items list: ' + str(items_list))

    for n, item in enumerate(items_list):

        # wd:Q123 - wd prefix on valid q number
        if re.match(r'^wd:[Qq]\d+$', item) is not None:
            continue

        # Q123 - Valid Q number, no wd
        elif re.match(r'^[Qq]\d+$', item) is not None:
            items_list[n] = 'wd:' + item

        # 123 - Valid number, no Q or wd
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
                    items_list[n:n] = [x for x in pile_list]
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
                items_list.pop(n)  # Silently fail, remove the entry from list

        # No patterns match at all, silently get rid of bogus entry
        else:
            print("Popping item that didn't match anything: " + item)
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
    pagepile:27688
    """
    # print('** Testing items: ')
    print(item_string_to_wdq_list(items))
    # print(pagepile_id_to_qid_list(27688))
    '''
    print(wikititle_to_qid("en", "Kygo"))
    print(wikititle_to_qid("en", "Columbia_University"))
    print(wikititle_to_qid("en", "Barack Obama"))
    print(wikititle_to_qid("en", "Barack Hussein Obama"))
    '''
