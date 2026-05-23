from .graphical_ops import (OpenDistributionOperator, SwitchLabelingTabOperator,
                           PipeUpOperator, PipeDownOperator, ChangePipelineViewerTabOperator, AddFolderOperator)
from .io_ops import (ApplyLogPathOperator, OpenLogsOperator, SavePipelineAsOperator, LoadPipelineOperator)
from .pipeline_ops import (EditPipeOperator, PipeAddOperator, MenuOperator, PipeRemoveOperator,
                           CaptureObjectsOperator, CaptureTextureOperator, CaptureObjectPositionOperator,
                           PositionRemoveOperator, PositionAddOperator, AddMaterialToListOperator, RemoveMaterialFromListOperator,
                           CaptureValueNode, CaptureAndModifyNodeProperties, SavePipeOperator, ScanPipelineOperator,
                           IntoFolderOperator, ViewTargetSelectedOperator, CaptureCursorPositionOperator,
                           TypedSingleObjectTargeter, TypedNodeCaptureOperator)
from .distribution_ops import (AddDistributionOperator, RemoveDistributionOperator, AddImagePathOperator,
                               RemoveImagePathOperator, ColorGradientRemoveOperator, ColorGradientAddOperator,
                               ColorPaletteAddOperator, ColorPaletteRemoveOperator)
from .core_ops import GenerateOperator, PreviewOperator
from .labeling_ops import (AddLabelRuleOperator, RemoveLabelRuleOperator, AddLabelClassOperator, RemoveObjectLabelOperator,
                           AddObjectLabelOperator, RemoveLabelClassOperator, TargetObjectsLabelOperator,
                           AddEntityOperator, RemoveEntityOperator, SelectEntityOperator, TargetObjectsEntityOperator)
from .landmarks_operator import (AutoDetectBonesOperator, AddKeypointOperator, RemoveKeypointOperator,
                                 AddConnectionOperator, RemoveConnectionOperator,
                                 AddRigOperator, RemoveRigOperator)

operators = (

    #
    OpenDistributionOperator, PipeUpOperator, PipeDownOperator,
    ChangePipelineViewerTabOperator, AddFolderOperator,

    #
    ApplyLogPathOperator, OpenLogsOperator, SavePipelineAsOperator, LoadPipelineOperator, SwitchLabelingTabOperator,

    #
    EditPipeOperator, MenuOperator, PipeAddOperator, PipeRemoveOperator, CaptureObjectsOperator, CaptureTextureOperator,
    PositionRemoveOperator, PositionAddOperator, CaptureObjectPositionOperator, AddMaterialToListOperator, RemoveMaterialFromListOperator,
    CaptureAndModifyNodeProperties, CaptureValueNode, SavePipeOperator,  ScanPipelineOperator, IntoFolderOperator,
    ViewTargetSelectedOperator, CaptureCursorPositionOperator,TypedSingleObjectTargeter, TypedNodeCaptureOperator,

    #
    AddDistributionOperator, RemoveDistributionOperator, AddImagePathOperator, RemoveImagePathOperator,

    #
    GenerateOperator, PreviewOperator,

    #
    AddLabelRuleOperator, RemoveLabelRuleOperator, AddLabelClassOperator, RemoveObjectLabelOperator,
                           AddObjectLabelOperator, RemoveLabelClassOperator, TargetObjectsLabelOperator,
    AddEntityOperator, RemoveEntityOperator, SelectEntityOperator, TargetObjectsEntityOperator,
    #
    AutoDetectBonesOperator, AddKeypointOperator,   RemoveKeypointOperator,
        AddConnectionOperator, RemoveConnectionOperator, AddRigOperator, RemoveRigOperator,

)
