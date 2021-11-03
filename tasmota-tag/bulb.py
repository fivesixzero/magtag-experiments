
import json

class Bulb:

    def __init__(self, name: str):

        self.name = name
        self.power = 'ON'
        self.dimmer = '0'
        self.ct = '0'
        self.color = '0'

    def __repr__(self) -> str:
        return "Bulb: {} | Power: {}, Dimmer: {}, CT: {}, Color: {}".format(self.name, self.power, self.dimmer, self.ct, self.color)

    def set_status(self, power: str, dimmer: str, ct: str, color: str):
        self.power = power
        self.dimmer = dimmer
        self.ct = ct
        self.color = color