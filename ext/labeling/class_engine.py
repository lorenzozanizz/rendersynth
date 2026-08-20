from typing import Union, Any, Iterable, Dict, List, Optional, Collection
from  .bpy_properties import LabelClass, ObjectLabel, LabelRule

import bpy

class ClassificationEngine:
    """

    """

    def __init__(self, context):
        """

        :param context:
        """
        self.ctx = context
        self.labels_mappings: Dict[str, LabelClass] = { }  # obj_name -> class_id
        self.entity_mappings: Dict[str, LabelClass] = { }

        self.entity_data: Optional[Dict] = None

    def extract_entity_data(self) -> Dict[str, List[str]]:
        """

        :return:
        """
        entity_data = self.ctx.scene.labeling_data.entities

        ret_data = dict()
        for ent_declaration in entity_data:
            name = ent_declaration.entity_name
            components = [ comp.obj_name for comp in ent_declaration.obj_names ]
            ret_data[name] = components

        self.entity_data = ret_data
        return ret_data

    def get_entity_data(self) -> Optional[Dict[str, List[str]]]:
        return self.entity_data

    def extract_class_labels_data(self) -> Dict[str, Any]:
        """ Fully serializes the labeling configuration into JSON-compatible format.
            See extract_labels.py for implementation details.
        """
        label_data = self.ctx.scene.labeling_data
        labels = label_data.direct_labels
        classes = label_data.label_classes
        mapping_rules = label_data.label_rules
        entities = label_data.entities

        # Serialize label classes
        classes_data = []
        for cls in classes:
            classes_data.append({
                "name": cls.name,
                "class_id": cls.class_id,
                "parent_id": cls.parent_id,
                "color": list(cls.color),
            })

        # Serialize direct labels
        direct_labels_data = []
        for label in labels:
            obj_names = [obj_name.obj_name for obj_name in label.obj_names]
            direct_labels_data.append({
                "assignment_id": label.assignment_id,
                "obj_names": obj_names,
                "class_id": label.class_id,
                "is_entity": label.is_entity,
            })

        # Serialize label rules
        rules_data = []
        for rule in mapping_rules:
            rule_entry = {
                "rule_type": rule.rule_type,
                "class_id": rule.class_id,
            }

            if rule.rule_type == 'MATERIAL':
                rule_entry["material_name"] = rule.material_name
            elif rule.rule_type == 'NAME_CONTAINS':
                rule_entry["name_filter"] = rule.name_filter
            elif rule.rule_type == 'COLLECTION':
                rule_entry["collection_name"] = rule.collection_name

            rules_data.append(rule_entry)

        # Serialize entities
        entities_data = []
        for entity in entities:
            obj_names = [obj_name.obj_name for obj_name in entity.obj_names]
            entities_data.append({
                "entity_id": entity.entity_id,
                "entity_name": entity.entity_name,
                "obj_names": obj_names,
            })

        # Compile complete configuration
        serialized_data = {
            "settings": {
                "do_superclasses": label_data.do_superclasses,
                "use_rules": label_data.use_rules,
                "use_entities": label_data.use_entities,
                "default_class": label_data.default_class,
            },
            "label_classes": classes_data,
            "direct_labels": direct_labels_data,
            "label_rules": rules_data,
            "entities": entities_data,
        }

        return serialized_data

    def classify_visible_objects(self, target_blender_objects: Iterable[Any]) -> None:
        """

        :param target_blender_objects:
        :return:
        """

        # Populate the label mappings using the scene rules on the target objects.
        # First evaluate direct mappings, which have the highest priority
        label_data = self.ctx.scene.labeling_data
        labels = label_data.direct_labels
        classes = label_data.label_classes
        for label in labels:
            # Note: up to date there are no checks on actual uniqueness of the assignments.
            # the last assignment wins.
            if not self._sanitize_direct_mapping(label):
                continue

            names = label.obj_names
            label_cls = label.class_id
            target_class: Optional[LabelClass] = self.resolve_class_by_id(label_cls)
            if target_class is None:
                # There is a dangling reference. ignore (and report, maybe?)
                continue
            if label.is_entity:
                self.entity_mappings.update( { name.obj_name: target_class for name in names } )
            else:
                self.labels_mappings.update( { name.obj_name: target_class for name in names } )

        # then evaluate rules.
        do_use_rules = label_data.use_rules
        if not do_use_rules:
            return

        name_map = {obj.name: obj for obj in target_blender_objects}
        missing_names = set(name_map.keys()).difference(self.labels_mappings.keys())
        mapping_rules = label_data.label_rules

        for mapping_rule in mapping_rules:
            relevant_data = self._sanitize_rule_mapping(mapping_rule)
            if not relevant_data:
                continue
            # Attempt to map the object using each mapping rule. Do this instead of evaluating every rule,
            # (assuming there are only a few objects to be mapped)
            if len(missing_names) == 0:
               return
            # We are missing some names, lets try to see if the current rule absolves one of the missing names
            rule_type = mapping_rule.rule_type
            mapping_class = next((cls for cls in label_data.label_classes
                        if str(cls.class_id).lower() == mapping_rule.class_id.lower()), None)
            resolved = []

            if rule_type.lower() == "material":

                material = relevant_data
                for missing_name in missing_names:
                    obj = name_map.get(missing_name)
                    if obj and obj.data and hasattr(obj.data, 'materials'):
                        if material.name in obj.data.materials:
                            resolved.append(missing_name)

            elif rule_type.lower() == "name_contains":
                partial_match = mapping_rule.name_filter
                resolved = [name for name in missing_names
                            if partial_match.lower() in name.lower()]

            elif rule_type.lower() == "collection":
                collection = relevant_data

                collection_obj_names = set(obj.name for obj in collection.objects)
                resolved = missing_names & collection_obj_names

            for name in resolved:
                self.labels_mappings[name] = mapping_class
                missing_names.discard(name)

        return

    def get_classes(self) -> List[LabelClass]:
        label_data = self.ctx.scene.labeling_data
        return label_data.label_classes

    def resolve_class_by_id(self, class_id: Union[str, int]) -> Optional[LabelClass]:
        """ Resolve a LabelClass from a raw class_id, as stored e.g. on ObjectLabel,
        LabelRule, or RigItem.class_id. Comparison is done on the string
        representation, since class_id may come from an EnumProperty (str)
        while LabelClass.class_id may be stored as an int.

        :param class_id: The class_id to resolve.
        :return: The matching LabelClass, or None if class_id does not match
            any currently registered class.
        """
        classes = self.ctx.scene.labeling_data.label_classes
        return next((cls for cls in classes if str(cls.class_id) == str(class_id)), None)

    def ignore_default_class(self) -> bool:
        pass

    def get_default_class(self) -> Optional[LabelClass]:
        pass

    @staticmethod
    def _sanitize_direct_mapping(mapping: ObjectLabel) -> bool:
        names = mapping.obj_names
        if not names or names is None:
            return False
        if not mapping.class_id:
            return False
        return True

    @staticmethod
    def _sanitize_rule_mapping(mapping: LabelRule) -> Optional[Any]:

        relevant_data = True
        # Initially check that a mapping class is correclty provided.
        if not mapping.class_id:
            return None
        # For a "material" rule, we check if the material exists
        if mapping.rule_type.upper() == "MATERIAL":
            mat = mapping.material_name
            if not mat.strip():
                return None
            relevant_data = bpy.data.materials.get(mat)
            if relevant_data is None:
                return None

        # For a "Name contains" rule, we check if the partial match is not empty
        elif mapping.rule_type.upper() == "NAME_CONTAINS":
            name = mapping.name_filter
            if not name.strip():
                return None

        # For a "collection" rule, we check if the collection exists.
        elif mapping.rule_type.upper() == "COLLECTION":
            collection = mapping.collection_name
            if not collection.strip():
                return None
            relevant_data = bpy.data.collections.get(collection)
            if relevant_data is None:
                return None
        else: return None
        return relevant_data

    def map_obj(self, obj: Union[str, Any]) -> Optional[LabelClass]:
        """

        :param obj:
        :return:
        """
        if isinstance(obj, str):
            name = obj
        else: name = obj.name
        if name in self.labels_mappings:
            return self.labels_mappings[name]
        return None

    def map_entity(self, entity_name: str) -> Optional[LabelClass]:
        return self.entity_mappings.get(entity_name)

    def get_mapping(self) -> Dict[str, LabelClass]:
        return self.labels_mappings

    def _unpack_entities_into_objects(self, entities, name_mappings: Dict[str, LabelClass]) -> Dict[str, LabelClass]:
        """ Unpack classified entities into its object subcomponents. This does not
        overwrite the object class, which takes priority.

        :param entities: a dictionary mapping an entity to a class
        :param name_mappings: a dictionary to be updated containing mappings of object names to classes
        :return:
        """
        ent_data = self.get_entity_data()
        if ent_data is None:
            # We cannot do anything if entity data has not yet been extracted by the scene, avoid
            # making a mess
            return name_mappings
        for ent_name, ent_class in entities.items():
            components = ent_data.get(ent_name)
            if components is None:
                # Something is wrong, ignore it
                continue
            # Only update values which are not present yet, so we do not overwrite
            name_mappings.update({comp: ent_class for comp in components if name_mappings.get(comp, None) is None})
        return name_mappings

    def request_full_mapping(self, all_names: Collection[str]) -> Dict[str, LabelClass]:
        """ Given a list of all defined Blender objects in a given scene, returns a dictionary
        mapping an object to its LabelClass correspective object.

        :param all_names: All defined names
        :return: a mapping from the object name to its class.
        """

        entities = {}
        name_mappings = {}
        label_data = self.ctx.scene.labeling_data
        labels = label_data.direct_labels

        for label in labels:
            # Note: up to date there are no checks on actual uniqueness of the assignments.
            # the last assignment wins.
            if not self._sanitize_direct_mapping(label):
                continue

            names = label.obj_names
            label_cls = label.class_id
            target_class: Optional[LabelClass] = self.resolve_class_by_id(label_cls)
            if target_class is None:
                # There is a dangling reference. ignore (and report, maybe?)
                continue

            if label.is_entity:
                entities.update({name.obj_name: target_class for name in names})
            else:
                name_mappings.update({name.obj_name: target_class for name in names})

        name_mappings = self._unpack_entities_into_objects(entities, name_mappings)

        # Names requested that haven't been resolved by direct labels/entities yet.
        all_names_set = set(all_names)
        missing_names = all_names_set - name_mappings.keys()

        do_use_rules = label_data.use_rules
        if do_use_rules and missing_names:
            # Only build the name -> bpy object lookup if we actually need it for rules.
            name_map = all_names
            mapping_rules = label_data.label_rules

            for mapping_rule in mapping_rules:
                if not missing_names:
                    break

                relevant_data = self._sanitize_rule_mapping(mapping_rule)
                if not relevant_data:
                    continue

                mapping_class = next(
                    (cls for cls in label_data.label_classes
                     if str(cls.class_id).lower() == mapping_rule.class_id.lower()),
                    None,
                )
                if mapping_class is None:
                    # Dangling class reference on the rule so we skip it.
                    continue

                rule_type = mapping_rule.rule_type.lower()
                resolved = []

                if rule_type == "material":
                    material = relevant_data
                    for missing_name in missing_names:
                        obj = name_map.get(missing_name)
                        if obj and obj.data and hasattr(obj.data, "materials"):
                            if material.name in obj.data.materials:
                                resolved.append(missing_name)

                elif rule_type == "name_contains":
                    partial_match = mapping_rule.name_filter.lower()
                    resolved = [
                        name for name in missing_names
                        if partial_match in name.lower()
                    ]

                elif rule_type == "collection":
                    collection = relevant_data
                    collection_obj_names = {obj.name for obj in collection.objects}
                    resolved = list(missing_names & collection_obj_names)

                if mapping_class is None:
                    continue
                for name in resolved:
                    name_mappings[name] = mapping_class
                    missing_names.discard(name)

        # Future addition point anything still unresolved after direct labels/entities/rules
        # falls through here
        if missing_names:
            name_mappings.update(self._resolve_unmapped_names(missing_names))

        return name_mappings

    def _resolve_unmapped_names(self, _missing_names: Collection[str]) -> Dict[str, LabelClass]:
        """ Hook for assigning a fallback LabelClass to names that couldn't be
        resolved via direct labels, entities, or rules.

        default_cls = self.resolve_class_by_id(self.ctx.scene.labeling_data.default_class_id)
        return {
            name: default_cls for name in missing_names
        } if default_cls else { }
        """
        return {}