#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   snaphost to a static site

import pygruta
import pygruta.html as html
import pygruta.xml as xml
import glob, os, re

def snapshot(gruta, outdir, url_prefix=""):
    """ Creates a full snapshot of a Gruta site """

    def out(file, content):
        """ snapshots a file with possible directories """

        try:
            gruta.snapshot_files.remove(file)
        except:
            pass

        # create the path if it does not exist
        path = file.split("/")
        p = ""
        for sp in path[1:-1]:
            p += "/" + sp

            try:
                os.mkdir(p)
                gruta.log("INFO", "Snapshot: CREATE %s" % p)
            except:
                pass

        # convert content to binary
        if isinstance(content, str):
            content = content.encode("utf-8")

        # check if file didn't changed
        w = True
        try:
            f = open(file, "rb")
            o_content = f.read()
            f.close()

            if o_content == content:
                w = False
        except:
            pass

        if w:
            gruta.log("INFO", "Snapshot: WRITE %s" % file)
            with open(file, "wb") as f:
                f.write(content)


    def out_u(url):
        """ snapshots by url """

        status, body, ctype = gruta.get_handler(url)

        if status == 200:
            out(gruta.snapshot_outdir + url, body)

        return status


    # ensure there is a trailing /
    if outdir[-1] != "/":
        outdir += "/"

    # get all currently existent files
    gruta.snapshot_files = glob.glob(outdir + "**", recursive=True)
    gruta.snapshot_files.remove(outdir)

    # set the url prefix
    gruta.url_prefix = url_prefix

    # store the outdir (without the trailing slash)
    gruta.snapshot_outdir = outdir[0:-1]

    # IMAGES
    for i in gruta.images():
        out_u("/img/%s" % i)

    # STORIES
    for s in gruta.story_set():
        out_u("/%s/%s.html" % (s[0], s[1]))

    # INDEXES
    if gruta.story("info", "index"):
        out_u("/index.html")

    else:
        num    = int(gruta.template("cfg_index_num"))
        offset = 0

        while True:
            fn = "/~%d.html" % offset if offset else "/index.html"

            if out_u(fn) != 200:
                break

            offset += num


    # TOPICS
    num = int(gruta.template("cfg_topic_num"))

    for t in gruta.topics():
        # create an ATOM for the first page of the index
        out_u("/%s/atom.xml" % t)

        # if there is an index page, only generate that
        if gruta.story(t, "index") is not None:
            out_u("/%s/index.html" % t)
        else:
            offset = 0

            while True:
                if offset == 0:
                    fn = "/%s/index.html" % t
                else:
                    fn = "/%s/~%d.html" % (t, offset)

                if out_u(fn) != 200:
                    break

                offset += num


    # TAGS
    n_tags = 0

    for tag in gruta.tags():
        # html page
        out_u("/tag/%s.html" % tag)

        # ATOM feed for this tag
#        out_u("/tag/%s.xml" % tag)

        n_tags += 1

    # only create a tag index if there are tags
    if n_tags > 0:
        out_u("/tag/index.html")


    # RSS 2.0
    out_u("/rss.xml")

    # ATOM
    out_u("/atom.xml")

    # SITEMAP
    out_u("/sitemap.xml")

    # USERS
    for id in gruta.users():
        out_u("/user/%s.html" % id)

    # robots.txt
    out_u("/robots.txt")

    # twtxt.txt
    out_u("/twtxt.txt")

    # css
    out_u("/main.css")


    # cleanup
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
