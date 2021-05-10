import numpy as np
import pytest
from numpy.ctypeslib import as_array
from numpy.testing import assert_array_equal

from meshkernel import (
    DeleteMeshOption,
    GeometryList,
    Mesh2d,
    MeshRefinementParameters,
    OrthogonalizationParameters,
    ProjectToLandBoundaryOption,
    RefinementType,
)

cases_deletemeshoption_values = [
    (DeleteMeshOption.ALL_NODES, 0),
    (DeleteMeshOption.ALL_FACE_CIRCUMCENTERS, 1),
    (DeleteMeshOption.ALL_COMPLETE_FACES, 2),
]


@pytest.mark.parametrize("enum_val, exp_int", cases_deletemeshoption_values)
def test_deletemeshoption_values(enum_val: DeleteMeshOption, exp_int: int):
    """Tests the integer values of the `DeleteMeshOption` enum."""

    assert enum_val == exp_int


cases_projecttolandboundaryoption_values = [
    (ProjectToLandBoundaryOption.DO_NOT_PROJECT_TO_LANDBOUNDARY, 0),
    (ProjectToLandBoundaryOption.TO_ORIGINAL_NETBOUNDARY, 1),
    (ProjectToLandBoundaryOption.OUTER_MESH_BOUNDARY_TO_LANDBOUNDARY, 2),
    (ProjectToLandBoundaryOption.INNER_AND_OUTER_MESH_BOUNDARY_TO_LANDBOUNDARY, 3),
    (ProjectToLandBoundaryOption.WHOLE_MESH, 4),
]


@pytest.mark.parametrize("enum_val, exp_int", cases_projecttolandboundaryoption_values)
def test_projecttolandboundaryoption_values(
    enum_val: ProjectToLandBoundaryOption, exp_int: int
):
    """Tests the integer values of the `ProjectToLandBoundaryOption` enum."""

    assert enum_val == exp_int


cases_refinementtype_values = [
    (RefinementType.WAVE_COURANT, 1),
    (RefinementType.REFINEMENT_LEVELS, 2),
]


@pytest.mark.parametrize("enum_val, exp_int", cases_refinementtype_values)
def test_refinementtype_values(enum_val: RefinementType, exp_int: int):
    """Tests the integer values of the `RefinementType` enum."""

    assert enum_val == exp_int


def test_mesdh2d_constructor():
    """Tests the default values after constructing a `Mesh2d`."""

    node_x = np.array([0.0, 1.0, 1.0, 0.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.double)
    edge_nodes = np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=np.int32)

    mesh2d = Mesh2d(node_x, node_y, edge_nodes)

    assert mesh2d.node_x.size == 4
    assert mesh2d.node_y.size == 4
    assert mesh2d.edge_nodes.size == 8
    assert mesh2d.face_nodes.size == 0
    assert mesh2d.nodes_per_face.size == 0
    assert mesh2d.edge_x.size == 0
    assert mesh2d.edge_y.size == 0
    assert mesh2d.face_x.size == 0
    assert mesh2d.face_y.size == 0


def test_geometrylist_constructor():
    """Tests the default values after constructing a `GeometryList`."""

    x_coordinates = np.array([0.0], dtype=np.double)
    y_coordinates = np.array([1.0], dtype=np.double)
    geometry_list = GeometryList(x_coordinates, y_coordinates)

    assert geometry_list.x_coordinates.size == 1
    assert geometry_list.y_coordinates.size == 1
    assert geometry_list.values.size == 0
    assert geometry_list.geometry_separator == -999.0
    assert geometry_list.inner_outer_separator == -998.0


def test_orthogonalizationparameters_constructor():
    """Tests the default values after constructing a `OrthogonalizationParameters`."""

    parameters = OrthogonalizationParameters()

    assert parameters.outer_iterations == 2
    assert parameters.boundary_iterations == 25
    assert parameters.inner_iterations == 25
    assert parameters.orthogonalization_to_smoothing_factor == 0.975
    assert parameters.orthogonalization_to_smoothing_factor_at_boundary == 1.0
    assert parameters.areal_to_angle_smoothing_factor == 1.0


def test_meshrefinementparameter_constructor_defaults():
    """Tests the default values after constructing a `MeshRefinementParameters`."""

    parameters = MeshRefinementParameters(
        False, True, 1.0, RefinementType.WAVE_COURANT, False, True
    )

    assert parameters.refine_intersected is False
    assert parameters.use_mass_center_when_refining is True
    assert parameters.min_face_size == 1.0
    assert parameters.refinement_type is RefinementType.WAVE_COURANT
    assert parameters.connect_hanging_nodes is False
    assert parameters.account_for_samples_outside_face is True
    assert parameters.max_refinement_iterations == 10
