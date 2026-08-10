

class ThermalSettings:
    pass

class ThermalSection:
    """ Draws the thermal labeling configuration: material definitions,
     configuration for the thermal dynamics, etcetera """

    @staticmethod
    def draw(layout, context):
        settings = context.scene.thermal_settings
