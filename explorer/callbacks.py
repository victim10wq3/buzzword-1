"""
buzzword explorer: callbacks
"""
from math import ceil
import os
import pandas as pd
from buzz.exceptions import DataTypeError
from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from explore.models import Corpus as CorpusModel

from django.conf import settings
from .chart import _df_to_figure
from .helpers import (
    _add_links,
    _cast_query,
    _get_specs_and_corpus,
    _special_search,
    _translate_relative,
    _tuple_or_list,
    _update_concordance,
    _update_conll,
    _update_frequencies,
    _make_multiword_query,
    _correct_page,
    _filter_corpus,
    _sort_corpus,
)
from .lang import LANGUAGES

from .main import app
from .strings import _make_search_name, _make_table_name, _search_error, _table_error

from . import style

from buzzword.utils import management_handling

if not management_handling():
    from start.apps import corpora, initial_tables, initial_concs

# we can't keep tables in dcc.store, they are too big. so we keep all here with
# a tuple that can identify them (ideally, even dealing with user sessions)
# todo: improve this
FREQUENCY_TABLES = dict()


@app.expanded_callback(
    Output("input-box", "placeholder"),  # Output("gram-select", "disabled")],  # swisslaw
    [Input("search-target", "value")],
    [State("language-switch", "on")],
)
def _correct_placeholder(value, lang, **kwargs):
    """
    More accurate placeholder text when doing dependencies
    """
    if value is None:
        return no_update

    return "Enter search query..." if not lang else "Suchabfrage eingeben..."

    # tofix
    mapped = {
        "t": "Enter Tgrep2 query...",
        "d": "Enter depgrep query",
        "describe": 'Enter depgrep query (e.g. l"man" = f"nsubj")',
    }
    # disable_gram = value in mapped
    return mapped.get(value, default)  # , disable_gram


@app.expanded_callback(
    [
        Output("tab-dataset", "style"),
        Output("tab-frequencies", "style"),
        Output("tab-chart", "style"),
        Output("tab-concordance", "style"),
    ],
    [Input("tabs", "value")],
    [State("search-from", "value")],
)
def render_content(tab, search_from, **kwargs):
    """
    Tab display callback. If the user clicked this tab, show it, otherwise hide
    """
    outputs = []
    for i in ["dataset", "frequencies", "chart", "concordance"]:
        if tab == i:
            outputs.append({"display": "block"})
        else:
            outputs.append({"display": "none"})
    return outputs


# one for each chart space
for i in range(1, 6):

    @app.expanded_callback(
        Output(f"chart-{i}", "figure"),
        [Input(f"figure-button-{i}", "n_clicks")],
        [
            State(f"chart-from-{i}", "value"),
            State(f"chart-type-{i}", "value"),
            State(f"chart-top-n-{i}", "value"),
            State(f"chart-transpose-{i}", "on"),
            State("session-tables", "data"),
            State("slug", "title"),
        ],
    )
    def _new_chart(
        n_clicks, table_from, chart_type, top_n, transpose, session_tables, slug, **kwargs,
    ):
        """
        Make new chart by kind. Do it 5 times, once for each chart space
        """
        # before anything is loaded, do nothing
        if n_clicks is None:
            return no_update
        # get correct dataset to chart
        conf = CorpusModel.objects.get(slug=slug)

        if str(table_from) in session_tables:
            this_table = session_tables[str(table_from)]
            df = FREQUENCY_TABLES[_tuple_or_list(this_table, tuple)]
        else:
            df = initial_tables[slug]

        # transpose and cut down items to plot
        if transpose:
            df = df.T
        df = df.iloc[:, :top_n]
        # generate chart
        return _df_to_figure(df, chart_type)


@app.expanded_callback(
    [Output("loading-main", "className"), Output("loading-main", "fullscreen")],
    [Input("everything", "children")],
    [],
)
def _on_load_callback(n_clicks, **kwargs):
    """
    This gets triggered on load; we use it to fix loading screen
    """
    return "loading-non-main", False



def _filter_view(corpus, page_current, page_size, editable, add_governor, slug):
    """
    Helper to return when just filtering corpus
    """
    filtered_corpus_size = len(corpus)
    corpus = _correct_page(corpus, page_current, page_size)
    cols, data = _update_conll(corpus, editable, drop_govs=add_governor, slug=slug)
    return (
        cols,
        data,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        ceil(filtered_corpus_size / page_size),
    )


def _sort_view(corpus, page_current, page_size, editable, add_governor, slug):
    """
    Helper to return when just sorting corpus
    """
    corpus = _correct_page(corpus, page_current, page_size)
    cols, data = _update_conll(corpus, editable, drop_govs=add_governor, slug=slug)
    return (
        cols,
        data,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
    )


def _pagechange_view(corpus, page_current, page_size, editable, add_governor, slug):
    """
    Helper to return when just changing pages
    """
    corpus_size = len(corpus)
    corpus = _correct_page(corpus, page_current, page_size)
    cols, data = _update_conll(corpus, editable, drop_govs=add_governor, slug=slug)
    return (
        cols,
        data,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        page_current,
        ceil(corpus_size / page_size),
    )



def _show_dataset_view(corpus, page_current, page_size, editable, add_governor, slug, show_dataset=None):
    """
    Helper to return when just showing a different dataset
    """
    corpus_size = len(corpus)
    corpus = _correct_page(corpus, page_current, page_size)
    cols, data = _update_conll(corpus, editable, drop_govs=add_governor, slug=slug)
    return (
        cols,
        data,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        show_dataset,
        no_update,
        no_update,
        ceil(corpus_size / page_size),
    )


def _actual_search(corpus, col, search_string, skip, multiword, no_use_regex):
    """
    # do ngramming stuff...disabled for now
    # if gram_select:
    #   df = getattr(corpus.near, col)(search_string, distance=gram_select)
    # skip/just searches

    Returns: df/None, msg/None
    """
    # depgrep/tgrep search types
    if col in {"t", "d", "describe"}:
        df, msg = _special_search(corpus, col, search_string, skip, multiword)
        if msg:
            return None, msg
        return df, None
    search = _cast_query(search_string, col)
    method = "just" if not skip else "skip"
    extra = dict() if no_use_regex else dict(regex=False, exact_match=True)
    # try to do the just/skip search
    try:
        df = getattr(getattr(corpus, method), col)(search, **extra)
        # check for matches
        if df is not None and len(df):
            return df, None
        return None, "No results found, sorry."
    except Exception as err:
        msg = f"Search error: {str(err)}"
        return None, msg


@app.callback(
    [
        Output("conll-view", "columns"),
        Output("conll-view", "data"),
        Output("search-from", "options"),
        Output("search-from", "value"),
        Output("search-from", "disabled"),
        Output("dialog-search", "displayed"),
        Output("dialog-search", "message"),
        Output("conll-view", "row_deletable"),
        Output("session-search", "data"),
        Output("session-clicks-clear", "data"),
        Output("session-clicks-show", "data"),
        Output("session-clicks-search", "data"),
        Output("session-current-conll-page", "data"),
        Output("conll-view", "page_count"),
    ],
    [
        Input("search-button", "n_clicks"),
        Input("clear-history", "n_clicks"),
        Input("show-this-dataset", "n_clicks"),
        Input("conll-view", "page_current"),
        Input("conll-view", "sort_by"),
        Input("conll-view", "filter_query"),
    ],
    [
        State("search-from", "value"),
        State("skip-switch", "on"),
        State("search-target", "value"),
        State("input-box", "value"),
        State("use-regex", "on"),
        # State("gram-select", "value"),
        State("search-from", "options"),
        State("session-search", "data"),
        State("session-clicks-clear", "data"),
        State("session-clicks-show", "data"),
        State("session-clicks-search", "data"),
        State("slug", "title"),
        State("language-switch", "on"),
        State("session-current-conll-page", "data"),
    ],
)
def _new_search(
    n_clicks,
    cleared,
    show_dataset,
    page_current,
    sort_by,
    filters,
    search_from,
    skip,
    col,
    search_string,
    no_use_regex,
    # gram_select,
    search_from_options,
    session_search,
    session_clicks_clear,
    session_clicks_show,
    session_clicks_search,
    slug,
    lang,
    conll_page,
    **kwargs,
):
    """
    Callback when a new search is submitted

    Validate input, run the search, store data and display things
    """
    # the first callback, before anything is loaded. Just do nothing
    if n_clicks is None and page_current == conll_page and not sort_by and not filters:
        return [no_update] * 14

    # do we actually need to do a search? (search was clicked and isn't the same as it was)
    clearing_history = cleared is not None and cleared > session_clicks_clear
    doing_search = n_clicks is not None and n_clicks > session_clicks_search and not clearing_history

    # some constants
    conf = CorpusModel.objects.get(slug=slug)
    max_row, max_col = settings.TABLE_SIZE
    corpus_size = len(corpora[slug])
    editable = bool(search_from)
    specs, corpus = _get_specs_and_corpus(search_from, session_search, corpora, slug)

    # if the user has done clear history, restore the tool to default state
    # we have to do this near the top, because otherwise sorting can get caught
    if clearing_history:
        # remove previous searches
        session_search.clear()
        # get the whole corpus and paginate it
        corpus = corpora[slug]
        corpus_size = len(corpus)
        corpus = _correct_page(corpus, page_current, settings.PAGE_SIZE)
        cols, data = _update_conll(corpus, False, drop_govs=conf.add_governor, slug=slug)
        name = _make_search_name(conf.name, corpus_size, session_search, int(lang))
        search_from = [dict(value=0, label=name)]
        # set number of clicks at last moment
        session_clicks_clear = cleared
        return (
            cols,
            data,
            search_from,
            0,
            True,
            False,
            "",
            False,
            session_search,
            session_clicks_clear,
            session_clicks_show,
            0,
            conll_page,
            ceil(corpus_size / settings.PAGE_SIZE),
        )

    # collect the values we need for returning from sorting, pagination, filtering etc.
    sort_page_filter = [page_current, settings.PAGE_SIZE, editable, conf.add_governor, slug]

    # do filtering. if anything was done, filtered is true, and return via helper
    corpus, filtered = _filter_corpus(corpus, filters, doing_search)
    if filtered and not doing_search:
        return _filter_view(corpus, *sort_page_filter)

    # do sorting. if anything was done, corpus_sorted is true
    corpus, corpus_sorted = _sort_corpus(corpus, sort_by, doing_search)
    # if just sorting, or if sort was returned to normal (2nd case), return
    # todo, may need to improve this...
    if (corpus_sorted and not doing_search) or (not sort_by and not doing_search):
        return _sort_view(corpus, *sort_page_filter)

    # if changing page, return the correct page data
    if conll_page != page_current:
        return _pagechange_view(corpus, *sort_page_filter)

    # user clicked the show button, show the selected (i.e. search_from) corpus
    if show_dataset and show_dataset != session_clicks_show:
        return _show_dataset_view(corpus, *sort_page_filter, show_dataset=show_dataset)

    # search doesn't validate. in this case, show the error and return previous state
    # todo: use messaging framework for this, not alert popup
    msg = _search_error(col, search_string)
    if msg:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            True,
            msg,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    # on first search, spec is slug name, so it goes here.
    this_search = [specs, col, skip, search_string, no_use_regex]  # regex needed
    # have we already done this exact search? compare previous searches for same data
    # if we have done it, we can return that one instead.
    exists = next((i for i in session_search.values() if this_search == list(i)[:5]), False)
    if exists:
        msg = "Table already exists. Switching to that one to save memory."
        df = corpus.iloc[exists[-1]]
        num_pages = ceil(len(df) / settings.PAGE_SIZE)
        df, _ = _filter_corpus(df, filters, False)
        df, _ = _sort_corpus(df, sort_by, False)
        df = _correct_page(df, page_current, settings.PAGE_SIZE)
        cols, data = _update_conll(df, bool(search_from), drop_govs=conf.add_governor, slug=slug)
        return (
            cols,
            data,
            search_from_options,
            exists[-3],
            no_update,
            True,
            msg,
            True,
            no_update,
            no_update,
            no_update,
            n_clicks,
            conll_page,
            num_pages,
        )

    # if the query has spaces, we need to prepare for multiword search
    multiword = " " in search_string.strip() and col not in {"t", "d"}
    if multiword:
        search_string, multiword = _make_multiword_query(search_string.strip(), col, no_use_regex)
        col = "d"

    # DO THE ACTUAL SEARCH HERE
    df, msg = _actual_search(corpus, col, search_string, skip, multiword, no_use_regex)
    # if it failed, we can return
    if msg:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            not bool(session_search),
            bool(msg),
            msg,
            bool(search_from), # row deletable
            no_update,
            no_update,
            no_update,
            n_clicks,
            no_update,
            no_update
        )

    # multiword queries add info to the dataset, the _position column. so, update this...
    # todo: this is NOT the correct way to handle this. it needs to go in session data...
    if multiword and df is not None:
        reference = corpora[slug]
        reference["_position"] = df["_position"]
        corpora[slug] = reference

    # assign this successful search  an id
    new_value = len(session_search) + 1
    # add the results of this search to the session data
    this_search += [new_value, len(df), list(df["_n"])]
    # store the search info
    session_search[new_value] = _tuple_or_list(this_search, list)
    # figure out sort, filter, pagination...
    num_pages = ceil(len(df) / settings.PAGE_SIZE)
    df, _ = _filter_corpus(df, filters, False)
    df, _ = _sort_corpus(df, sort_by, False)
    df = _correct_page(df, page_current, settings.PAGE_SIZE)
    current_cols, current_data = _update_conll(df, True, conf.add_governor, slug=slug)
    name = _make_search_name(this_search, corpus_size, session_search, int(lang))
    new_option = dict(value=new_value, label=name)
    enu = enumerate(search_from_options)
    index_for_option = next(i for i, s in enu if s["value"] == search_from)
    search_from_options.insert(index_for_option + 1, new_option)

    return (
        current_cols,
        current_data,
        search_from_options,
        new_value,
        False,  # is there a msg, no
        bool(msg),
        msg,
        True,  # row deletable, always yes
        session_search,
        session_clicks_clear,
        session_clicks_show,
        n_clicks,
        conll_page,
        num_pages,
    )


@app.expanded_callback(
    [
        Output("freq-table", "columns"),
        Output("freq-table", "data"),
        Output("freq-table", "editable"),
        Output("chart-from-1", "value"),
        Output("chart-from-1", "options"),
        Output("chart-from-2", "options"),
        Output("chart-from-3", "options"),
        Output("chart-from-4", "options"),
        Output("chart-from-5", "options"),
        Output("dialog-table", "displayed"),
        Output("dialog-table", "message"),
        Output("freq-table", "row_deletable"),
        Output("session-tables", "data"),
        Output("session-clicks-table", "data"),
        #Output("freq-table", "style_data_conditional")
    ],
    [Input("table-button", "n_clicks"), Input("freq-table", "data_previous"),],
    [
        State("freq-table", "columns"),
        State("freq-table", "data"),
        State("search-from", "value"),
        State("show-for-table", "value"),
        State("subcorpora-for-table", "value"),
        State("relative-for-table", "value"),
        State("sort-for-table", "value"),
        # State("multiindex-switch", "on"),
        # State("content-table-switch", "on"),
        State("chart-from-1", "options"),
        State("chart-from-1", "value"),
        State("session-search", "data"),
        State("session-tables", "data"),
        State("session-clicks-table", "data"),
        State("slug", "title"),
    ],
)
def _new_table(
    n_clicks,
    prev_data,
    current_cols,
    current_data,
    search_from,
    show,
    subcorpora,
    relkey,
    sort,
    # multiindex_columns,
    # content_table,
    table_from_options,
    nv1,
    session_search,
    session_tables,
    session_click_table,
    slug,
    **kwargs,
):
    """
    Callback when a new freq table is generated. Same logic as new_search.
    """
    # do nothing if not yet loaded
    if n_clicks is None:
        raise PreventUpdate

    conf = CorpusModel.objects.get(slug=slug)

    # because no option below can return initial table, rows can now be deleted
    row_deletable = True

    specs, corpus = _get_specs_and_corpus(search_from, session_search, corpora, slug)

    # figure out sort, subcorpora,relative and keyness
    sort = sort or "total"
    if subcorpora == "_corpus":
        subcorpora = None
    relative, keyness = _translate_relative(relkey)

    # check if there are any validation problems
    if session_click_table != n_clicks:
        updating = False
        session_click_table = n_clicks
    elif prev_data is not None:
        # if number of rows has changed
        if len(prev_data) != len(current_data):
            updating = True
        # if number of columns has changed
        if len(prev_data[0]) != len(current_data[0]):
            updating = True

    msg = _table_error(show, subcorpora, updating)
    this_table_list = [
        specs,
        list(show),
        subcorpora,
        relative,
        keyness,
        sort,
        # multiindex_columns,
        # content_table,
    ]
    this_table_tuple = _tuple_or_list(this_table_list, tuple)

    # if table already made, use that one
    key = next((k for k, v in session_tables.items() if this_table_list == v), False)
    idx = key if key is not False else len(session_tables) + 1

    # if we are updating the table:
    if updating:
        # get the whole table from master dict of them
        table = FREQUENCY_TABLES[this_table_tuple]
        # fix rows and columns
        table = table[[i["id"] for i in current_cols[1:]]]
        table = table.loc[[i["_" + table.index.name] for i in current_data]]
        # store table again with same key
        FREQUENCY_TABLES[this_table_tuple] = table
    elif key is not False:
        msg = "Table already exists. Switching to that one to save memory."
        table = FREQUENCY_TABLES[this_table_tuple]
    # if there was a validation problem, juse use last table (?)
    elif msg:
        if session_tables:
            # todo: figure this out...use current table instead?
            key, value = list(session_tables.items())[-1]
            table = FREQUENCY_TABLES[_tuple_or_list(value, tuple)]
            # todo: more here?
        else:
            table = initial_tables[slug]
    else:
        # generate table
        method = "table"
        table = getattr(corpus, method)(
            show=show,
            subcorpora=subcorpora,
            relative=relative if relative != "corpus" else corpora[slug],
            keyness=keyness,
            sort=sort,
            multiindex_columns=False,  # multiindex_columns,
            show_frequencies=relative is not False and relative is not None,
        )
        # round df if floats are used
        if relative is not False or keyness:
            table = table.round(2)

        # untested
        if table.index.name == "file":
            table.index = table.index.to_series().apply(os.path.basename)
            table.index = table.index.to_series().str.replace(".conllu", "", regex=False)

        # cannot hash a corpus, which relative may be.
        # none will denote corpus as reference
        if isinstance(relative, pd.DataFrame):
            relative = None

        # then store the search information in store/freq table spaces
        session_tables[idx] = this_table_list
        FREQUENCY_TABLES[this_table_tuple] = table

    if updating:
        cols, data, style_index = no_update, no_update, no_update
    else:

        style_index = style.FILE_INDEX
        style_index["if"]["column_id"] = table.index.name

        table = table.reset_index()
        max_row, max_col = settings.TABLE_SIZE
        tab = table.iloc[:max_row, :max_col]
        # todo: swisslaw, multi and content
        cols, data = _update_frequencies(tab, True, False)

    if not msg and not updating:
        table_name = _make_table_name(this_table_list)
        option = dict(value=idx, label=table_name)
        table_from_options.append(option)

    return (
        cols,
        data,
        True,
        idx,
        table_from_options,
        table_from_options,
        table_from_options,
        table_from_options,
        table_from_options,
        bool(msg),
        msg,
        row_deletable,
        session_tables,
        session_click_table,
        #style_index
    )


@app.expanded_callback(
    [
        Output("conc-table", "columns"),
        Output("conc-table", "data"),
        Output("dialog-conc", "displayed"),
        Output("dialog-conc", "message"),
        Output("session-clicks-conc", "data"),
        Output("session-current-conc-page", "data"),
    ],
    [
        Input("update-conc", "n_clicks"),
        Input("conc-table", "page_current"),
        Input("conc-table", "sort_by"),
        Input("conc-table", "filter_query"),
    ],
    [
        State("show-for-conc", "value"),
        State("search-from", "value"),
        State("session-search", "data"),
        State("slug", "title"),
        State("session-clicks-conc", "data"),
        State("session-current-conc-page", "data"),
    ],
)
def _new_conc(
    n_clicks,
    page_current,
    sort_by,
    filter,
    show,
    search_from,
    session_search,
    slug,
    session_clicks_conc,
    conc_page,
    **kwargs,
):
    """
    Callback for concordance. Handles filter, sort, pagination and update
    """
    if n_clicks is None and page_current == conc_page and not sort_by and not filter:
        return [no_update] * 6

    msg = False

    if not show:
        show = "w"

    if n_clicks and not search_from and show != "w":
        msg = "You cannot concordance an entire corpus. Please do a search first."
        return no_update, no_update, bool(msg), msg, n_clicks, page_current

    if not search_from and show == "w":
        conc = initial_concs[slug]
    else:
        specs, corpus = _get_specs_and_corpus(search_from, session_search, corpora, slug)
        met = ["file", "s", "i"]
        if isinstance(corpus, pd.DataFrame):
            for feat in {"speaker", "year"}:
                if feat in corpus.columns:
                    met.append(feat)

        conc = corpus.conc(show=show, metadata=met, window=(100, 100), n=settings.MAX_CONC)
        conc = _add_links(conc, slug=slug, conc=True)
        conc["file"] = conc["file"].apply(os.path.basename)
        conc["file"] = conc["file"].str.replace(".conllu", "", regex=False)

    # if just changing page
    if conc_page != page_current:
        corpus_size = len(conc)
        conc = _correct_page(conc, page_current, settings.PAGE_SIZE)
        cols, data = _update_concordance(conc, True)
        return cols, data, bool(msg), msg, n_clicks, page_current

    # yes, these are named corpus, but they are fine on conc as well
    conc, corpus_sorted = _sort_corpus(conc, sort_by, False)
    conc, corpus_filtered = _filter_corpus(conc, filter, False)
    conc = _correct_page(conc, page_current, settings.PAGE_SIZE)
    cols, data = _update_concordance(conc, deletable=True)
    return cols, data, bool(msg), msg, n_clicks, page_current


@app.expanded_callback(
    [Output("matching-text", "children"), Output("skip-switch", "className")],
    [Input("skip-switch", "on")],
)
def _matching_not_matching(on, **kwargs):
    """
    Change the text for matching/not matching
    """
    text = "matching" if not on else "not matching"
    classname = "colour-off" if not on else "colour-on"
    return text, classname


@app.expanded_callback(
    [Output("regex-text", "children"), Output("use-regex", "className")],
    [Input("use-regex", "on")],
)
def _use_regex(on, **kwargs):
    """
    Colour and change the text for simple/regex search
    """
    text = "simple search" if not on else "regular expression"
    classname = "colour-off" if not on else "colour-on"
    return text, classname


@app.expanded_callback(
    [Output("multiindex-switch", "disabled"), Output("multiindex-switch", "on")],
    [Input("multiindex-switch", "n_clicks"), Input("show-for-table", "value")],
    [State("multiindex-switch", "on")],
)
def _multiindex(_, show, on, **kwargs):
    """
    Multiindexing --- disabled currently
    """
    if not show or len(show) < 2:
        return True, False
    return False, on


@app.expanded_callback(
    [Output("language-text", "children"), Output("language-switch", "className")],
    [Input("language-switch", "on")],
)
def _switch_language(on, **kwargs):
    """
    Switch the text of the active language
    """
    text = "English" if not on else "German"
    classname = "colour-off" if not on else "colour-on"
    return text, classname


language_outputs = [Output(c, f) for c, f in sorted(LANGUAGES) if f]
language_states = [State(c, f) for c, f in sorted(LANGUAGES) if f]


@app.expanded_callback(
    language_outputs, [Input("language-switch", "on")], language_states,
)
def _change_language(lang, *args, **kwargs):
    """
    Change the language of the entire explorer
    """
    if lang is None:
        return no_update
    return [v[int(lang)] for (_, f), v in sorted(LANGUAGES.items()) if f]
