#!/usr/bin/env python3
# Runs a headless browser so we can scrape sites that use javascript to load everything
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# SQL ORM stuff
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker
# DB Tables
from db_tables import *

db_url = 'sqlite:///nanohub_tags.db'
engine = create_engine(db_url, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Used for setting any add/update times
runtime = datetime.datetime.now()


def safe_commit():
    """
    Ensures data is committed to the database safely
    :return:
    """
    # Ensure a session exists
    if session:
        try:
            # Commit the session
            session.commit()
        except Exception as ex:
            print(ex)
            # Undo the session's changes
            session.rollback()
            # Halt execution
            raise


def get_resources_by_tag(tag: str, search_driver, tag_driver, force: bool = False, verbose: bool = False, debug: bool = False):
    page = 0
    while True:
        url = 'https://nanohub.org/tags/' + tag.replace(' ',
                                                        '+') + '/resources?limit=1000&sort=date&active=resources&start=' + str(
            1000 * page)
        if verbose:
            print(url)
        search_driver.get(url)
        try:
            results = search_driver.find_element_by_css_selector('.results')
            results = results.find_elements_by_tag_name('li')
            print("Found {} results for {}".format(len(results), tag))

            for index, result in enumerate(results):
                title = result.find_element_by_class_name('title').text

                resource_id = result.find_element_by_class_name('title').find_element_by_tag_name('a').get_attribute(
                    'href')[30:]

                Resource(
                    id=resource_id,
                    title=title
                ).merge(session, timestamp=runtime)

                authors = result.find_element_by_class_name('details').text

                try:
                    authors = authors[authors.index(':: ') + 3:].split(', ')
                except ValueError:
                    authors = None

                if authors is not None:
                    if verbose:
                        print('\t[{} {:0{}d}/{}] Found {} author(s) for resource {}'.format(tag, index + 1,
                                                                                            len(str(len(results))),
                                                                                            len(results), len(authors),
                                                                                            resource_id))
                    for author in authors:
                        if debug:
                            print('[DEBUG] link_author(author: {}, resource_id: {})'.format(author, resource_id))
                        link_author(author, resource_id, verbose, debug)
                else:
                    if verbose:
                        print('\t[{} {:0{}d}/{}] Found 0 authors for resource {}'.format(tag, index + 1,
                                                                                         len(str(len(results))),
                                                                                         len(results), resource_id))

                # Reduce request count by only grabbing tags for content with low tag counts
                if len(session.query(TagLink).filter(TagLink.resource_id == resource_id).all()) < 2 or force:
                    if debug:
                        print('[DEBUG] get_resource_tags(resource: {})'.format(resource_id))
                    get_resource_tags(resource_id, tag_driver, verbose, debug)
                else:
                    if debug:
                        print('[DEBUG] link_tag(tag: None, display_str: {}, resource_id: {})'.format(tag, resource_id))
                    link_tag(None, tag, resource_id, verbose)
                    if verbose:
                        print('\t[{} {:0{}d}/{}] Skipping resource {} for now'.format(tag, index + 1,
                                                                                      len(str(len(results))),
                                                                                      len(results), resource_id))

            if len(results) % 1000 == 0:
                page = page + 1
            else:
                break
        except Exception as ex:
            print("\tError: {}".format(ex))
            break


def add_author(name: str, verbose: bool = False):
    # Check if the author is in the database before adding
    if not session.query(exists().where(Author.name == name)).scalar():
        Author(name=name).save(session, timestamp=runtime)
        if verbose:
            print("\tAdded new author: {}".format(name))


def link_author(name: str, resource: str, verbose: bool = False, debug: bool = False):
    # Ensure the author is in the database
    if debug:
        print('\t[DEBUG] add_author(name: {})'.format(name))
    add_author(name, verbose)

    # Get the automatically generated author id
    author_id = session.query(Author).filter(Author.name == name).first()
    if author_id:
        author_id = author_id.id
        if debug:
            print('\t[DEBUG] author_id = {}'.format(author_id))
    else:
        author_id = None
        if debug:
            print('\t[DEBUG] author_id = None')

    # Ensure no author-resource link exists
    if author_id and not session.query(AuthorLink).filter(AuthorLink.resource_id == resource).filter(
            AuthorLink.author_id == author_id).scalar():
        # Add the author and resource
        AuthorLink(
            author_id=author_id,
            resource_id=resource
        ).save(session, timestamp=runtime)
    elif not author_id and debug:
        print('\t[DEBUG] No author exists for id {}'.format(author_id))
    elif author_id and session.query(AuthorLink).filter(AuthorLink.resource_id == resource).filter(
            AuthorLink.author_id == author_id).scalar() and debug:
        print('\t[DEBUG] Author link exists')


def add_tag(tag: str, display_str: str, verbose: bool = False):
    # Check if the tag is in the database before adding
    if not session.query(exists().where(Tag.tag == tag)).scalar():
        Tag(tag=tag, display=display_str).save(session, timestamp=runtime)
        if verbose:
            print("Added new tag: {} displayed as {}".format(tag, display_str))


def link_tag(tag: str, display_str: str, resource: str, verbose: bool = False, debug: bool = False):
    # Note: tag is not guaranteed, display_str is
    # Add the tag to the database if we have all information
    if tag:
        if verbose:
            print("\tAttempting to add tag: {}".format(display_str))
        if debug:
            print('\t[DEBUG] add_tag(tag: {}, display_str: {})'.format(tag, display_str))
        add_tag(tag, display_str, verbose)

    # Get the automatically generated tag id
    tag_id = session.query(Tag).filter(Tag.display == display_str).first()
    if tag_id:
        tag_id = tag_id.id
        if debug:
            print('\t[DEBUG] tag_id = {}'.format(tag_id))
    else:
        tag_id = None
        if debug:
            print('\t[DEBUG] tag_id = None')

    # Ensure no tag-resource link exists
    if tag_id and not session.query(TagLink).filter(TagLink.resource_id == resource).filter(
            TagLink.tag_id == tag_id).scalar():
        # Link the tag and resource
        TagLink(
            tag_id=tag_id,
            resource_id=resource
        ).save(session, timestamp=runtime)
    elif not tag_id and debug:
        print('\t[DEBUG] No tag exists for tag {}'.format(display_str))
    elif tag_id and session.query(TagLink).filter(TagLink.resource_id == resource).filter(
            TagLink.tag_id == tag_id).scalar() and debug:
        print('\t[DEBUG] Tag link exists')


def get_resource_tags(resource: str, driver, verbose: bool = False, debug: bool = False):
    url = 'https://nanohub.org/resources/' + resource
    driver.get(url)
    try:
        current_tags = [str]
        site_tags = [str]
        tags = session.query(TagLink).filter(TagLink.resource_id == resource).all()
        for tag in tags:
            tag_str = session.query(Tag).filter(Tag.id == tag.tag_id).first().tag
            if tag_str not in current_tags:
                current_tags.append(tag_str)

        tags = driver.find_element_by_css_selector('.tags')
        tags = tags.find_elements_by_tag_name('li')
        if verbose:
            print('\tFound {} tag(s) for resource {}'.format(len(tags), resource))
        for tag in tags:
            display = tag.text
            tag = tag.find_element_by_class_name('tag').get_attribute('href')[25:]
            link_tag(tag, display, resource, verbose)
            site_tags.append(tag)
        for tag in current_tags:
            if tag not in site_tags:
                if verbose:
                    print("\tTag {} has been removed from resource {}".format(tag, resource))
                tag_id = session.query(Tag).filter(Tag.tag == tag).first().id
                session.query(TagLink).filter(TagLink.tag_id == tag_id).filter(TagLink.resource_id == resource).delete()
    except Exception as ex:
        print("\tError: {}".format(ex))


def main():
    print(runtime)
    import argparse

    parser = argparse.ArgumentParser(description='A tool to scrape nanohub resource information')
    parser.add_argument('-t', nargs='+', type=str, help='Scrape given tag(s)', dest='tag')
    parser.add_argument('-rt', nargs='+', type=str, help='Remove given tag(s)', dest='rtag')
    parser.add_argument('-r', nargs='+', type=str, help='Scrape given resource(s)', dest='resource')
    parser.add_argument('-rr', nargs='+', type=str, help='Remove given resource(s)', dest='rresource')
    parser.add_argument('-v', action="store_true", default=False, help='Enable verbose output', dest='verbose')
    parser.add_argument('-d', action="store_true", default=False, help='Enable debugging output', dest='debug')
    parser.add_argument('-f', action="store_true", default=False, help='Don\'t limit requests', dest='force')
    parser.add_argument('--version', action="version", version='%(prog)s 1.0')

    results = parser.parse_args()
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    search_driver = webdriver.Chrome(options=chrome_options)
    tag_driver = webdriver.Chrome(options=chrome_options)

    if results.tag is not None and results.resource is None and results.rtag is None and results.rresource is None:
        # Scrapes a list of tags
        print(results.tag)
        for tag in results.tag:
            get_resources_by_tag(tag, search_driver, tag_driver, results.force, results.verbose, results.debug)
    elif results.tag is None and results.resource is not None and results.rtag is None and results.rresource is None:
        # Scrapes a list of resources
        print(len(results.resource))
        for resource in results.resource:
            get_resource_tags(resource, tag_driver, results.verbose, results.debug)
    elif results.tag is None and results.resource is None and results.rtag is not None and results.rresource is None:
        # Deletes a tag
        session.query(Tag).filter(Tag.display == results.rtag).first().delete(session)
    elif results.tag is None and results.resource is None and results.rtag is None and results.rresource is not None:
        # Remove a resource
        session.query(Resource).filter(Resource.id == results.rresource).first().delete(session)
    else:
        # Invalid combination of arguments
        pass

    # Get all the tags so we can scrape them all
    # tags = session.query(Tag).all()

    # for index, tag in enumerate(tags):
    #    print("[{:0{}d}/{}] Fetching videos for: {}".format(index+1, len(str(len(tags))), len(tags), tag.tag))
    #    get_resources_by_tag(tag.tag, search_driver, tag_driver)


if __name__ == "__main__":
    main()

# TODO: Make generating reports part of this script functionality
# TODO: Figure out the sql for authors
