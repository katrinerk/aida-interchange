class TypedDescriptor:
    def __init__(self, enttype, descriptor):
        self.enttype = enttype
        self.descriptor = descriptor

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'enttype': self.enttype,
            'descriptor': self.descriptor,
        }
        return str(rep)


class EntType:
    def __init__(self, typ, subtype=None, subsubtype=None):
        self.type = typ
        self.subtype = subtype
        self.subsubtype = subsubtype

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'type': self.type,
            'subtype': self.subtype,
            'subsubtype': self.subsubtype
        }
        return str(rep)

    def get_type_score(self, target):
        score = 0
        if self.type.strip().lower() == target['type'].strip().lower():
            score += 1
        if self.subtype.strip().lower() == target['subtype'].strip().lower():
            score += 1
        if self.subsubtype.strip().lower() == target['subsubtype'].strip().lower():
            score += 1

        return score


class TextDescriptor:
    def __init__(self, doceid, start, end):
        self.descriptor_type = "Text"
        self.doceid = doceid
        self.start = start
        self.end = end

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'doceid': self.doceid,
            'start': self.start,
            'end': self.end,
        }
        return str(rep)

    def evaluate_node(self, justification_node):
        """
        This function evaluates the TextDescriptor against a justificaiton node to determine if there is a match.
        :param justification_node: AidaNode
        :return: True/False
        """
        justification_source = next(iter(justification_node.get("source"))).value.strip()
        if not justification_source:
            return False

        if justification_source == self.doceid:
            justification_start_offset = str(next(iter(justification_node.get("startOffset"))).value).strip()
            justification_end_offset = str(next(iter(justification_node.get("endOffsetInclusive"))).value).strip()

            if justification_start_offset == self.start and justification_end_offset == self.end:
                return True
        return False


class StringDescriptor:
    def __init__(self, name_string):
        self.descriptor_type = "String"
        self.name_string = name_string

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'name_string': self.name_string,
        }
        return str(rep)

    def evaluate_node(self, subject_node):
        """
        A function to evaluate teh StringDescriptor against a subject node to determine if there is a match.
        :param subject_node: AidaNode
        :return: True/False
        """
        name_set = subject_node.get('hasName')
        if not name_set:
            return False
        if self.name_string in name_set:
            return True
        return False


class VideoDescriptor:
    def __init__(self, doceid, keyframe_id, top_left, bottom_right):
        self.descriptor_type = "Video"
        self.doceid = doceid
        self.keyframe_id = keyframe_id
        self.top_left = top_left
        self.bottom_right = bottom_right

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'doceid': self.doceid,
            'keyframe_id': self.keyframe_id,
            'top_left': self.top_left,
            'bottom_right': self.bottom_right,
        }
        return str(rep)


class ImageDescriptor:
    def __init__(self, doceid, top_left, bottom_right):
        self.descriptor_type = "Image"
        self.doceid = doceid
        self.top_left = top_left
        self.bottom_right = bottom_right

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'doceid': self.doceid,
            'top_left': self.top_left,
            'bottom_right': self.bottom_right,
        }
        return str(rep)

    def evaluate_node(self, justification_node, bounding_box_node):
        justification_source = next(iter(justification_node.get('source'))).value.strip()
        bb_upper_left_x = str(next(iter(bounding_box_node.get('boundingBoxUpperLeftX'))).value).strip()
        bb_upper_left_y = str(next(iter(bounding_box_node.get('boundingBoxUpperLeftY'))).value).strip()
        bb_lower_right_x = str(next(iter(bounding_box_node.get('boundingBoxLowerRightX'))).value).strip()
        bb_lower_right_y = str(next(iter(bounding_box_node.get('boundingBoxLowerRightY'))).value).strip()

        upper_left_x, upper_left_y = self.top_left.strip().split(',')
        lower_right_x, lower_right_y = self.bottom_right.strip().split(',')

        if justification_source == self.doceid and upper_left_x == bb_upper_left_x:
            if upper_left_y == bb_upper_left_y:
                if lower_right_x == bb_lower_right_x:
                    if lower_right_y == bb_lower_right_y:
                        return True
        return False


class KBDescriptor:
    def __init__(self, kbid):
        self.descriptor_type = "KB"
        self.kbid = kbid

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        rep = {
            'kbid': self.kbid,
        }
        return str(rep)

    def evaluate_node(self, link_node):
        print("EVER ENTERING?")

        link_value_set = link_node.get('linkTarget')
        if not link_value_set:
            return False

        link_value = next(iter(link_value_set)).value.strip()
        print(link_value)
        print(self.kbid)
        input()
        if self.kbid == link_value:
            return True

        return False
