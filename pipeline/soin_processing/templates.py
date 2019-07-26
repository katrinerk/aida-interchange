EP_REP_TEMPLATE = {
    "variable": None,
    "typed_descriptor_list": [],
}

TYPED_DESCRIPTOR_TEMPLATE = {
    'enttype': None,
    'descriptor': None,
}

IMAGE_DESCRIPTOR_REP_TEMPLATE = {
    "doceid": None,
    "top_left": None,
    "bottom_right": None
}

TEXT_DESCRIPTOR_REP_TEMPLATE = {
    "doceid": None,
    "start": None,
    "end": None,
}

STRING_DESCRIPTOR_REP_TEMPLATE = {
    "name_string": None,
}

KB_DESCRIPTOR_REP_TEMPLATE = {
    "kbid": None,
}

VIDEO_DESCRIPTOR_REP_TEMPLATE = {
    'doceid': None,
    'keyframe_id': None,
    'top_left': None,
    'bottom_right': None,
}

FACET_TEMPLATE = {
    "ERE": [],
    "temporal": [],
    "statements": [],
    "queryConstraints": {},
}