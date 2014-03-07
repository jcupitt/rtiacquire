#!/usr/bin/python

# simple rectangle class

def enum(**enums):
    return type('Enum', (), enums)
Edge = enum(N = 1, S = 2, E = 3, W = 4, 
            NW = 5, NE = 6, SW = 7, SE = 8,
            NONE = 9)
Edges = [Edge.NW, Edge.NE, Edge.SW, Edge.SE, Edge.N, Edge.S, Edge.E, Edge.W]

class Rect:
    """simple rectangle class"""
    def __init__(self, left = 0, top = 0, width = 0, height = 0):
        self.left = int(left)
        self.top = int(top)
        self.width = int(width)
        self.height = int(height)

    def __str__(self):
        return "<Rect: left = %d, top = %d, width = %d, height = %d>" % \
            (self.left, self.top, self.width, self.height)

    def clone(self):
        return Rect(self.left, self.top, self.width, self.height)

    def margin_adjust(self, n):
        self.left -= int(n)
        self.top -= int(n)
        self.width += 2 * int(n)
        self.height += 2 * int(n)

    def right(self):
        return self.left + self.width

    def bottom(self):
        return self.top + self.height

    def normalise(self):
        if self.width < 0:
            self.left += self.width
            self.width *= -1
        if self.height < 0:
            self.top += self.height
            self.height *= -1

    def empty(self):
        return self.width == 0 or self.height == 0

    def centre(self):
        return (self.left + self.width / 2, self.top + self.height / 2)

    def includes_point(self, left, top):
        return self.left <= left and \
                self.top <= top and \
                self.right() >= left and \
                self.bottom() >= top 

    def includes_rect(self, other):
        return self.left <= other.left and \
                self.top <= other.top and \
                self.right() >= other.right() and \
                self.bottom() >= other.bottom()

    def union(self, other):
        if self.empty():
            return other
        elif other.empty():
            return self
        else:
            left = min(self.left, other.left)
            right = max(self.right(), other.right())
            top = min(self.top, other.top)
            bottom = max(self.bottom(), other.bottom())

            return Rect(left, top, right - left, bottom - top)

    def intersection(self, other):
        left = max(self.left, other.left)
        right = min(self.right(), other.right())
        top = max(self.top, other.top)
        bottom = min(self.bottom(), other.bottom())

        return Rect(left, top, right - left, bottom - top)

    def corner(self, edge):
        corner = None

        if edge == Edge.NW:
            corner = Rect(self.left, self.top)
        if edge == Edge.NE:
            corner = Rect(self.right(), self.top)
        if edge == Edge.SW:
            corner = Rect(self.left, self.bottom())
        if edge == Edge.SE:
            corner = Rect(self.right(), self.bottom())

        if edge == Edge.N:
            corner = Rect(self.left, self.top, self.width, 0)
        if edge == Edge.S:
            corner = Rect(self.left, self.bottom(), self.width, 0)
        if edge == Edge.W:
            corner = Rect(self.left, self.top, 0, self.height)
        if edge == Edge.E:
            corner = Rect(self.right(), self.top, 0, self.height)

        return corner

    def which_corner(self, corner_size, x, y):
        for edge in Edges:
            corner = self.corner(edge)
            corner.margin_adjust(corner_size)
            if corner.includes_point(x, y):
                return edge

        return Edge.NONE
