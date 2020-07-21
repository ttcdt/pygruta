#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

import time

class Cache:
    def __init__(self, ttl=3600):
        self.data  = {}
        self.ttl   = ttl
        self.rtime = time.time()

    def get(self, index, tag=""):
        """ gets an object from a cache """

        object, state, context = None, 0, ""

        ce = self.data.get(index)

        if ce is not None:
            if time.time() < ce["expires"]:
                # cache hit
                object  = ce["object"]
                context = ce["context"]

                if ce["tag"] == tag:
                    # same tag: client already has it
                    state = 1
                else:
                    # different or no tag: we have it but client don't
                    state = -1
            else:
                # expired
                self.data.pop(index)

        return object, state, context

    def put(self, index, object, ttl=120, tag="", context=""):
        """ puts an object into a cache """

        if object is not None:
            self.data[index] = {
                "object":   object,
                "expires":  time.time() + ttl,
                "tag":      tag,
                "context":  context
            }
        else:
            try:
                # un-cache
                self.data.pop(index)
            except:
                pass

    def clear(self, force=False):
        """ clear all entries """

        if force or time.time() > self.rtime + self.ttl:
            self.data  = {}
            self.rtime = time.time()
