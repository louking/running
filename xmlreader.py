import sys
from xml import sax
from textnormalize import text_normalize_filter
import pdb

#Subclass from ContentHandler in order to gain default behaviors
class label_dict_handler(sax.ContentHandler):
    #Define constants for important states
    CAPTURE_KEY = 1
    CAPTURE_LABEL_ITEM = 2
    CAPTURE_ADDRESS_ITEM = 3

    def __init__(self):
        self.label_dict = {}
        #Track the item being constructed in the current dictionary
        self._item_to_create = None
        self._state = None
        return

    def startElement(self, name, attributes):
        if name == u"label":
            self._curr_label = {}
        if name == u"address":
            self._address = {}
        if name == u"name":
            self._state = self.CAPTURE_KEY
        if name == u"quote":
            self._item_to_create = name
            self._state = self.CAPTURE_LABEL_ITEM
        if name in [u"street", u"city", u"state"]:
            self._item_to_create = name
            self._state = self.CAPTURE_ADDRESS_ITEM
        return

    def endElement(self, name):
        if name == u"address":
            self._curr_label["address"] = self._address
        if name in [u"quote", u"name", u"street", u"city", u"state"]:
            self._state = None
        return

    def characters(self, text):
        if self._state == self.CAPTURE_KEY:
            self.label_dict[text] = self._curr_label
        curr_dict = None
        if self._state == self.CAPTURE_ADDRESS_ITEM:
            curr_dict = self._address
        if self._state == self.CAPTURE_LABEL_ITEM:
            curr_dict = self._curr_label
        print repr(text), curr_dict
        if curr_dict is not None:
            if curr_dict.has_key(self._item_to_create):
                curr_dict[self._item_to_create] += text
            else:
                curr_dict[self._item_to_create] = text
        return

if __name__ == "__main__":
    parser = sax.make_parser()
    downstream_handler = label_dict_handler()
    #upstream: the parser; downstream: the next handler in the chain
    filter_handler = text_normalize_filter(parser, downstream_handler)
    #XMLFilterBase is designed so that the filter takes on much of the
    #interface of the parser itself, including the "parse" method
    filter_handler.parse(sys.argv[1])
    label_dict = downstream_handler.label_dict 
    pdb.set_trace()