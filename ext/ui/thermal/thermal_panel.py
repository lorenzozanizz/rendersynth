

class ThermalSettings:
    pass

class LandmarkSection:
    """ Draws the thermal labeling configuration: material definitions,
     configuration for the thermal dynamics, etcetera """

    @staticmethod
    def draw(layout, context):
        settings = context.scene.thermal_settings
