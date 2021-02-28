#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   snapshot to a static site

import pygruta
import pygruta.html as html
import pygruta.xml as xml
import glob, os, re

def set_outdir(gruta, outdir):
    """ sets the snapshot output directory """

    # ensure there is a trailing /
    if outdir[-1] != "/":
        outdir += "/"

    # get all currently existent files
    gruta.snapshot_files = glob.glob(outdir + "**", recursive=True)
    gruta.snapshot_files.remove(outdir)

    # store the outdir (without the trailing slash)
    gruta.snapshot_outdir = outdir[0:-1]


def url_list(gruta, outdir):
    """ Generates the urls to be snapshotted """

    set_outdir(gruta, outdir)

    def d(file):
        try:
            gruta.snapshot_files.remove(gruta.snapshot_outdir + file)
        except:
            pass

        return file

    # IMAGES
    for i in gruta.images():
        yield d("/img/%s" % i)

    # STORIES
    for s in gruta.story_set():
        yield d("/%s/%s.html" % (s[0], s[1]))

    # INDEXES
    if gruta.story("info", "index"):
        yield d("/index.html")

    else:
        num      = int(gruta.template("cfg_index_num"))
        offset   = 0
        i_topics = gruta.template("cfg_index_topics").split(":")
        max      = len(list(gruta.story_set(topics=i_topics)))

        while offset < max:
            fn = "/~%d.html" % offset if offset else "/index.html"

            yield d(fn)

            offset += num

    # TOPICS
    num = int(gruta.template("cfg_topic_num"))

    for t in gruta.topics():
        # create an ATOM for the first page of the index
        yield d("/%s/atom.xml" % t)

        # if there is an index page, only generate that
        if gruta.story(t, "index") is not None:
            yield d("/%s/index.html" % t)
        else:
            offset = 0
            max    = len(list(gruta.story_set(topics=[t])))

            while offset < max:
                if offset == 0:
                    fn = "/%s/index.html" % t
                else:
                    fn = "/%s/~%d.html" % (t, offset)

                yield d(fn)

                offset += num

    # TAGS
    n_tags = 0

    for tag in gruta.tags():
        # html page
        yield d("/tag/%s.html" % tag)

        # ATOM feed for this tag
#        yield d("/tag/%s.xml" % tag)

        n_tags += 1

    # only create a tag index if there are tags
    if n_tags > 0:
        yield d("/tag/index.html")


    # RSS 2.0
    yield d("/rss.xml")

    # ATOM
    yield d("/atom.xml")

    # SITEMAP
    yield d("/sitemap.xml")

    # USERS
    for id in gruta.users():
        yield d("/user/%s.html" % id)

    # robots.txt
    yield d("/robots.txt")

    # twtxt.txt
    yield d("/twtxt.txt")

    # css
    yield d("/style.css")


    # delete all files in the snapshot folder that were not generated
    l = list(gruta.snapshot_files)
    l.sort(reverse=True);

    for f in l:
        try:
            os.unlink(f)
            gruta.log("INFO", "Snapshot: DELETE %s" % f)
        except:
            try:
                os.rmdir(f)
                gruta.log("INFO", "Snapshot: RMDIR %s" % f)
            except:
                pass


def store(gruta, file, content):
    """ writes a file if it's different """

    # convert content to binary
    if isinstance(content, str):
        content = content.encode("utf-8")

    # read already stored content (can fail if file does not exist yet)
    try:
        f = open(file, "rb")
        o_content = f.read()
        f.close()
    except:
        o_content = ""

    # different?
    if content != o_content:
        # write as is
        try:
            f = open(file, "wb")
            f.write(content)
            f.close()
            gruta.log("INFO", "Snapshot: WRITE %s" % file)

        except:
            # may have failed because path does not exist,
            # so try to create it
            path = file.split("/")
            p = ""
            for sp in path[1:-1]:
                p += "/" + sp

                try:
                    os.mkdir(p)
                    gruta.log("INFO", "Snapshot: CREATE %s" % p)
                except:
                    pass

            # retry write
            try:
                f = open(file, "wb")
                f.write(content)
                f.close()
                gruta.log("INFO", "Snapshot: WRITE %s" % file)
            except:
                gruta.log("ERROR", "Snapshot: cannot WRITE %s" % file)


def snap_url(gruta, outdir, url):
    """ Snapshots one url """
    url = url.replace("%20", " ")

    status, body, ctype = gruta.get_handler(url)

    if status == 200:
        store(gruta, gruta.snapshot_outdir + url, body)


def snapshot(gruta, outdir, url_prefix=""):
    """ Creates a full snapshot of a Gruta site """

    # set the url prefix
    gruta.url_prefix = url_prefix

    # iterates the urls
    for url in url_list(gruta, outdir):
        snap_url(gruta, outdir, url)
