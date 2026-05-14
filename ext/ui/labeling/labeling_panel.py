from .landmark_section import LandmarkSection

from ...constants import *
from ...operators.names import Labels

from bpy.types import UIList, PropertyGroup, Panel

class LabelClassesUIList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene

        row = layout.row(align=True)
        sub = row.column(align=True)
        sub.scale_x = 0.3
        sub.prop(item, 'color', text='')
        row.separator()
        row.prop(item, 'name', text='', emboss=False)
        if scene.labeling_data.do_superclasses:
            # Display the class superclass
            row.serarator()
            id = item.parent_id
            # Search for another class with the parent id.
            # row.prop(item, 'parent_id')
        row.separator()
        row.prop(item, 'class_id', emboss=False, text="")



class ObjectLabelsUIList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene

        # The class has to be an enum depending on the classes currentlyr egistered.
        # Now show a small band with the class color for visual aid.
        # Find the corresponding class, put its color for clarity.
        row = layout.row(align=True)
        cls = next((cls for cls in scene.labeling_data.label_classes
                    if str(cls.class_id).lower() == item.class_id.lower()), None)
        if cls:
            sub = row.column(align=True)
            sub.scale_x = 0.3
            sub.prop(cls, 'color', text='')
            row.separator()

        text_label = str([n_prop.obj_name for n_prop in item.obj_names]) \
             if len(item.obj_names) != 0 else "None"

        ico_name = 'OBJECT_DATA' if not item.is_entity else 'GHOST_DISABLED'


        row.label(text=text_label, icon=ico_name)
        row.operator(Labels.CAPTURE_OBJECTS_LABEL.value, icon="EYEDROPPER", text="").target_rule_obj_id = (
            item.assignment_id)
        # Ensure that the entities are enabled
        use_entities = scene.labeling_data.use_entities
        if use_entities:
            # Add the entity selection operator
            row.operator(Labels.SELECT_ENTITY_LABEL.value, text="", icon="GHOST_DISABLED").target_rule_obj_id = (
                item.assignment_id
            )
        row.separator()
        row.prop(item, 'class_id', emboss=False, text="")
        if cls:
            sub = row.column(align=True)
            sub.scale_x = 0.4
            sub.label(text=f"({cls.class_id})")

class NamedEntitiesUIList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)

        text_label = str([n_prop.obj_name for n_prop in item.obj_names]) \
             if len(item.obj_names) != 0 else "None"

        row.label(text=text_label, icon='OBJECT_DATA')
        row.operator(Labels.CAPTURE_OBJECTS_ENTITY.value, icon="EYEDROPPER", text="").target_entity_id = (
            item.entity_id
        )

        row.separator()
        row.prop(item, 'entity_name', emboss=False, text="")
        sub = row.column(align=True)
        sub.scale_x = 0.4
        sub.label(text=f"({item.entity_id})")

class LabelRulesUIList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        scene = context.scene

        row = layout.row(align=True)
        row.prop(item, 'rule_type', text="")
        row.separator()
        if item.rule_type == 'MATERIAL':
            row.prop(item, 'material_name', text="")
        elif item.rule_type == 'NAME_CONTAINS':
            row.prop(item, 'name_filter', text="")
        elif item.rule_type == 'COLLECTION':
            row.prop(item, 'collection_name', text="")
        else:
            return
        row.separator()
        # The class has to be an enum depending on the classes currently registered.
        # Now show a small band with the class color for visual aid.
        # Find the corresponding class, put its color for clarity.
        row.prop(item, 'class_id', text="")

        row = layout.row(align=True)
        cls = next((cls for cls in scene.labeling_data.label_classes
                    if str(cls.class_id).lower() == item.class_id.lower()), None)
        if cls:
            sub = row.column(align=True)
            sub.scale_x = 0.3
            sub.prop(cls, 'color', text='')
            row.separator()


class LabelingPanel(Panel):

    bl_label = "Labeling"
    bl_idname = panel_conflict_rename("labeling")
    bl_category = PANEL_CATEGORY
    bl_space_type = 'VIEW_3D'
    bl_options = { 'DEFAULT_CLOSED' }
    bl_region_type = 'UI'

    def draw(self, context):

        layout = self.layout

        layout.label(text="Labeling mode", icon="INFO")
        row = layout.row()
        active = context.window_manager.get('labeling_tab', 'class_tab')

        for tab_id, tab_label in [('class_tab', 'Classes'), ('landmark_tab', 'Landmarks')]:
            row.operator(Labels.SWITCH_LABEL_SECTION.value,
                text=tab_label,
                depress=(tab_id == active),
                emboss=True).tab = tab_id

        layout.separator()
        if active == 'class_tab':
            self.draw_classes(layout, context)
        elif active == 'landmark_tab':
            self.draw_landmarks(layout, context)

    @staticmethod
    def draw_landmarks(layout, context):
        LandmarkSection.draw(layout, context)

    @staticmethod
    def draw_classes(layout, context):
        scene = context.scene
        labeling_data = scene.labeling_data

        box = layout.box()
        box.label(text="Classes", icon='GROUP')
        row = box.row()
        row.template_list(
            LabelClassesUIList.__name__,
            'labeling_classes_list',
            labeling_data, 'label_classes',
            labeling_data, 'class_active_index'
        )
        col = row.column()
        col.operator(Labels.ADD_LABEL_CLASS.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_LABEL_CLASS.value, icon='REMOVE', text='')

        row = layout.row(align=True)
        row.label(text="Default Class")
        row.prop(labeling_data, 'default_class', text="")

        # Draw the color associated with the default class.
        cls = next((cls for cls in scene.labeling_data.label_classes
                    if str(cls.class_id).lower() == labeling_data.default_class.lower()), None)
        if cls:
            sub = row.column(align=True)
            sub.scale_x = 0.4
            sub.prop(cls, 'color', text='')
            row.separator()

        layout.prop(labeling_data, 'use_entities', text="Define multi-object entities")
        # Allow the user to create multi-object entities.
        if labeling_data.use_entities:
            # Show the entity creation UI list.

            box = layout.box()
            box.label(text="Named Entities", icon='GHOST_ENABLED')
            row = box.row()
            row.template_list(
                NamedEntitiesUIList.__name__,
                'entities_list',
                labeling_data, 'entities',
                labeling_data, 'entities_active_index'
            )
            col = row.column()
            col.operator(Labels.ADD_ENTITY.value, icon='ADD', text='')
            col.operator(Labels.REMOVE_ENTITY.value, icon='REMOVE', text='')


        layout.separator()
        layout.label(text="Class assignment")
        box = layout.box()
        box.label(text="Object Labels", icon='OBJECT_DATA')
        row = box.row()
        row.template_list(
            ObjectLabelsUIList.__name__,
            'object_labels_list',
            labeling_data, 'direct_labels',
            labeling_data, 'direct_active_index'
        )
        col = row.column()
        col.operator(Labels.ADD_OBJECT_LABEL.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_OBJECT_LABEL.value, icon='REMOVE', text='')

        layout.prop(labeling_data, 'use_rules', text="Use Assignment Rules")
        if labeling_data.use_rules:
            box = layout.box()
            box.label(text="Labeling Rules", icon='SOLO_ON')

            legend = box.row(align=True)  # ensure same number of columns
            for lab in ("Type", "Setting", "Class"):
                legend.label(text=lab)
            legend.enabled = False
            row = box.row()
            row.template_list(
                LabelRulesUIList.__name__,
                'label_rules_list',
                labeling_data, 'label_rules',
                labeling_data, 'rule_active_index'
            )
            col = row.column()
            col.operator(Labels.ADD_LABEL_RULE.value, icon='ADD', text='')
            col.operator(Labels.REMOVE_LABEL_RULE.value, icon='REMOVE', text='')

        # Show rule editor if selected
        """
        if labeling_data.label_rules:
            rule = labeling_data.label_rules[labeling_data.rule_active_index]
            box = layout.box()
            box.prop(rule, 'rule_type', text='Type')

            if rule.rule_type == 'MATERIAL':
                box.prop(rule, 'material_name', text='Material')
            elif rule.rule_type == 'NAME_CONTAINS':
                box.prop(rule, 'name_filter', text='Contains')
            elif rule.rule_type == 'COLLECTION':
                box.prop(rule, 'collection_name', text='Collection')

            box.prop(rule, 'class_id', text='Assign to Class')
            """