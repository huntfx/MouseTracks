"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Custom validators for Qt as I wasn't a fan of the default functionality

from __future__ import absolute_import

from .Qt import QtGui


class QStringValidator(QtGui.QValidator):
    """Custom string validator to only accept certain characters.
    It requires the widget as a workaround. (https://stackoverflow.com/a/23176248/2403000)
    """
    VALID_DEFAULT = ascii_letters + digits + ' _(),.:'

    def __init__(self, parent, valid=VALID_DEFAULT, replacement=None):
        QtGui.QValidator.__init__(self, parent)
        self.parent = parent
        self.valid = valid
        self.replacement = replacement
    
    def validate(self, current_text, cursor_pos):
        if any(i for i in current_text if i not in self.valid):
            return QtGui.QValidator.Invalid
        if current_text:
            return QtGui.QValidator.Acceptable
        return QtGui.QValidator.Intermediate

    def fixup(self, current_text):
        """Replace all invalid characters."""
        replacement = self.replacement if self.replacement is not None else ''
        converted_text = re.sub('[^{}]'.format(self.valid), replacement, current_text)
        self.parent.setText(converted_text)
        return converted_text


class QNumberValidator(QtGui.QValidator):
    """Custom validator for numbers since QIntValidator wasn't working well."""
    VALID_INT = '-0123456789'
    VALID_FLOAT = VALID_INT + '.'

    def __init__(self, parent, number_type=None, minimum=None, maximum=None):
        self.parent = parent
        if None not in (minimum, maximum) and minimum > maximum:
            raise ValueError('minimum value is higher than maximum')
        self.number_type = number_type or float
        self.minimum = minimum
        self.maximum = maximum
        QtGui.QValidator.__init__(self, parent)

    def validate(self, current_text, cursor_pos):
        if self.number_type == int:
            valid = self.VALID_INT
        elif self.number_type == float:
            valid = self.VALID_FLOAT
        else:
            raise TypeError('invalid number type "{}"'.format(self.number_type))

        #Check for invalid charaters
        if any(i for i in current_text if i not in valid) or any(i in current_text for i in ('..', '--', '.-')):
            return QtGui.QValidator.Invalid

        if current_text:
            if '-' in current_text[1:]:
                return QtGui.QValidator.Invalid #Number has minus inside it

            #Check start of number
            try:
                no_minus = current_text.lstrip('-')
                if no_minus[0] == '0':
                    try:
                        if no_minus[1] == '0':
                            return QtGui.QValidator.Invalid #Number starts with 00
                    except IndexError:
                        return QtGui.QValidator.Acceptable #Number is 0
                    return QtGui.QValidator.Intermediate #Number starts with 0
            except IndexError:
                return QtGui.QValidator.Intermediate #Number is just a minus

            #Check for leading or trailing decimals
            if current_text[0] == '.':
                return QtGui.QValidator.Intermediate #Number starts with decimal
            if current_text[-1] == '.':
                return QtGui.QValidator.Intermediate #Number ends with decimal

            #Check for range
            if self.minimum is not None and self.number_type(current_text) < self.minimum:
                return QtGui.QValidator.Intermediate #Number is too low
            if self.maximum is not None and self.number_type(current_text) > self.maximum:
                return QtGui.QValidator.Invalid #Number is too high

            return QtGui.QValidator.Acceptable
        return QtGui.QValidator.Intermediate #Number is empty
    
    def fixup(self, current_text):
        #Remove leading zeroes
        try:
            if current_text[0] == '0' and current_text[1] != '.':
                current_text = current_text[1:]
        except IndexError:
            pass

        #convert to number
        try:
            current_value = self.number_type(current_text)
        except ValueError:
            if self.number_type == int and current_text[-1] == '.':
                try:
                    current_value = self.number_type(current_text[:-1])
                except valueError:
                    current_value = self.number_type()
            else:
                current_value = self.number_type()

        #Apply minimum and maximum values
        if self.minimum is not None and current_value < self.minimum:
            current_value = self.number_type(self.minimum)
        if self.maximum is not None and current_value > self.maximum:
            current_value = self.number_type(self.maximum)

        self.parent.setText(str(current_value))
        return current_value