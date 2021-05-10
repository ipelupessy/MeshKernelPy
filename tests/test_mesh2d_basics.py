import numpy as np
import pytest
from numpy import ndarray
from numpy.testing import assert_array_equal
from pytest import approx

from meshkernel import (
    DeleteMeshOption,
    GeometryList,
    InputError,
    Mesh2d,
    Mesh2dFactory,
    MeshKernel,
    MeshKernelError,
    MeshRefinementParameters,
    RefinementType,
)


@pytest.fixture(scope="function")
def meshkernel_with_mesh2d():
    """Creates a new instance of 'meshkernel' and sets a Mesh2d with the specified dimensions.

    Args:
        rows (int): Number of node rows
        columns (int): Number of node columns

    Returns:
        MeshKernel: The created instance of `meshkernel`
    """

    def _create(rows: int, columns: int):
        mesh2d = Mesh2dFactory.create_rectilinear_mesh(rows, columns)
        mk = MeshKernel()

        mk.set_mesh2d(mesh2d)

        return mk

    return _create


cases_is_geometric_constructor = [(True), (False)]


@pytest.mark.parametrize("is_geometric", cases_is_geometric_constructor)
def test_constructor(is_geometric: bool):
    """Test if the constructor works"""
    MeshKernel(is_geometric)


def test_different_instances_have_different_ids():
    """Test if the meshkernelid of two instances differs"""
    mk_1 = MeshKernel()
    mk_2 = MeshKernel()

    assert mk_1._meshkernelid != mk_2._meshkernelid


def test_set_mesh2d_and_get_mesh2d():
    """Test to set a simple mesh and then get it again with new parameters

    3---2
    |   |
    0---1
    """
    mk = MeshKernel()

    edge_nodes = np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=np.int32)
    node_x = np.array([0.0, 1.0, 1.0, 0.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.double)

    input_mesh2d = Mesh2d(node_x, node_y, edge_nodes)
    mk.set_mesh2d(input_mesh2d)

    output_mesh2d = mk.get_mesh2d()

    # Test if the input and output differs
    assert_array_equal(output_mesh2d.edge_nodes, input_mesh2d.edge_nodes)
    assert_array_equal(output_mesh2d.node_x, input_mesh2d.node_x)
    assert_array_equal(output_mesh2d.node_y, input_mesh2d.node_y)

    # Test if faces are correctly calculated
    assert_array_equal(output_mesh2d.face_nodes, np.array([0, 1, 2, 3]))
    assert_array_equal(output_mesh2d.nodes_per_face, np.array([4]))
    assert_array_equal(output_mesh2d.face_x, np.array([0.5]))
    assert_array_equal(output_mesh2d.face_y, np.array([0.5]))

    # Test if edges are correctly calculated
    assert_array_equal(output_mesh2d.edge_x, np.array([0.5, 1.0, 0.5, 0.0]))
    assert_array_equal(output_mesh2d.edge_y, np.array([0.0, 0.5, 1.0, 0.5]))


def test_insert_edge_mesh2d(meshkernel_with_mesh2d: MeshKernel):
    """Test `insert_edge_mesh2d` by inserting one edge within a 2x2 Mesh2d.

    2---3
    |   |
    0---1
    """

    mk = meshkernel_with_mesh2d(2, 2)

    edge_index = mk.insert_edge_mesh2d(0, 3)

    mesh2d = mk.get_mesh2d()

    assert edge_index == 4
    assert mesh2d.node_x.size == 4
    assert mesh2d.edge_x.size == 5
    assert mesh2d.face_x.size == 2


def test_insert_node_mesh2d(meshkernel_with_mesh2d: MeshKernel):
    """Test `insert_node_mesh2d` with a 2x2 Mesh2d.

    2---3
    |   |
    0---1
    """

    mk = meshkernel_with_mesh2d(2, 2)

    node_index = mk.insert_node_mesh2d(1.5, 0.5)
    edge_index = mk.insert_edge_mesh2d(3, node_index)

    mesh2d = mk.get_mesh2d()

    assert node_index == 4
    assert mesh2d.node_x.size == 5
    assert edge_index == 4
    assert mesh2d.edge_x.size == 5


cases_delete_node_mesh2d = [
    (0, 0.0, 0.0),
    (1, 1.0, 0.0),
    (2, 2.0, 0.0),
    (3, 0.0, 1.0),
    (4, 1.0, 1.0),
    (5, 2.0, 1.0),
    (6, 0.0, 2.0),
    (7, 1.0, 2.0),
    (8, 2.0, 2.0),
]


@pytest.mark.parametrize("node_index, deleted_x, deleted_y", cases_delete_node_mesh2d)
def test_delete_node_mesh2d(
    meshkernel_with_mesh2d: MeshKernel,
    node_index: int,
    deleted_x: float,
    deleted_y: float,
):
    """Test `delete_node_mesh2d` by deleting a node from a 3x3 Mesh2d.

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2

    """
    mk = meshkernel_with_mesh2d(3, 3)

    mk.delete_node_mesh2d(node_index)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 8

    for x, y in zip(mesh2d.node_x, mesh2d.node_y):
        assert x != deleted_x or y != deleted_y


def test_delete_node_mesh2d_invalid_node_index(meshkernel_with_mesh2d: MeshKernel):
    """Test `delete_node_mesh2d` by passing a negative `node_index`."""

    mk = meshkernel_with_mesh2d(2, 2)

    with pytest.raises(InputError):
        mk.delete_node_mesh2d(-1)


cases_move_node_mesh2d = [
    (0, 0.0, 0.0),
    (1, 1.0, 0.0),
    (2, 2.0, 0.0),
    (3, 0.0, 1.0),
    (4, 1.0, 1.0),
    (5, 2.0, 1.0),
    (6, 0.0, 2.0),
    (7, 1.0, 2.0),
    (8, 2.0, 2.0),
]


@pytest.mark.parametrize("node_index, moved_x, moved_y", cases_move_node_mesh2d)
def test_move_node_mesh2d(
    meshkernel_with_mesh2d: MeshKernel, node_index: int, moved_x: float, moved_y: float
):
    """Test to move a node in a simple Mesh2d to new location.

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2

    """

    mk = meshkernel_with_mesh2d(3, 3)

    mk.move_node_mesh2d(5.0, 7.0, node_index)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x[node_index] == 5.0
    assert mesh2d.node_y[node_index] == 7.0

    for x, y in zip(mesh2d.node_x, mesh2d.node_y):
        assert x != moved_x or y != moved_y


def test_move_node_mesh2d_invalid_node_index(meshkernel_with_mesh2d: MeshKernel):
    """Test `move_node_mesh2d` by passing a negative `node_index`."""

    mk = meshkernel_with_mesh2d(2, 2)
    with pytest.raises(InputError):
        mk.move_node_mesh2d(5.0, 7.0, -1)


cases_delete_edge_mesh2d = [
    (0.5, 0.0),
    (1.5, 0.0),
    (0.0, 0.5),
    (1.0, 0.5),
    (2.0, 0.5),
    (0.5, 1.0),
    (1.5, 1.0),
    (0.0, 1.5),
    (1.0, 1.5),
    (2.0, 1.5),
    (0.5, 2.0),
    (1.5, 2.0),
]


@pytest.mark.parametrize("delete_x, delete_y", cases_delete_edge_mesh2d)
def test_delete_edge_mesh2d(
    meshkernel_with_mesh2d: MeshKernel, delete_x: float, delete_y: float
):
    """Test `delete_edge_mesh2d` by deleting an edge from a 3x3 Mesh2d.

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2

    """
    mk = meshkernel_with_mesh2d(3, 3)

    mk.delete_edge_mesh2d(delete_x, delete_y)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 9
    assert mesh2d.edge_x.size == 11
    assert mesh2d.face_x.size == 3

    for x, y in zip(mesh2d.edge_x, mesh2d.edge_y):
        assert x != delete_x or y != delete_y


cases_get_edge_mesh2d = [
    (0.5, 0.0, 2),
    (1.0, 0.5, 1),
    (0.5, 1.0, 3),
    (0.0, 0.5, 0),
]


@pytest.mark.parametrize("x, y, exp_index", cases_get_edge_mesh2d)
def test_get_edge_mesh2d(
    meshkernel_with_mesh2d: MeshKernel, x: float, y: float, exp_index: int
):
    """Test `get_edge_mesh2d` on a 2x2 Mesh2d.

        (3)
       2---3
    (0)|   |(1)
       0---1
        (2)

    """

    mk = meshkernel_with_mesh2d(2, 2)

    edge_index = mk.get_edge_mesh2d(x, y)

    assert edge_index == exp_index


cases_get_node_index_mesh2d = [
    (0.0, 0.0, 0),
    (0.4, 0.0, 0),
    (0.0, 0.4, 0),
    (1.0, 0.0, 1),
    (0.6, 0.0, 1),
    (1.0, 0.4, 1),
    (0.0, 1.0, 2),
    (0.4, 1.0, 2),
    (0.0, 0.6, 2),
    (1.0, 1.0, 3),
    (0.6, 1.0, 3),
    (1.0, 0.6, 3),
]


@pytest.mark.parametrize("x, y, exp_index", cases_get_node_index_mesh2d)
def test_get_node_index_mesh2d(
    meshkernel_with_mesh2d: MeshKernel, x: float, y: float, exp_index: int
):
    """Test `get_node_index_mesh2d` on a 2x2 Mesh2d.

    2---3
    |   |
    0---1

    """

    mk = meshkernel_with_mesh2d(2, 2)

    edge_index = mk.get_node_index_mesh2d(x, y, 0.5)

    assert edge_index == exp_index


def test_get_node_index_mesh2d_no_node_in_search_radius(
    meshkernel_with_mesh2d: MeshKernel,
):
    """Test `get_node_index` when there is no node within the search radius."""

    mk = meshkernel_with_mesh2d(2, 2)

    with pytest.raises(MeshKernelError):
        mk.get_node_index_mesh2d(0.5, 0.5, 0.4)


cases_delete_mesh2d_small_polygon = [
    (True, DeleteMeshOption.ALL_NODES, 4, 4, 1),
    (True, DeleteMeshOption.ALL_FACE_CIRCUMCENTERS, 16, 24, 9),
    (True, DeleteMeshOption.ALL_COMPLETE_FACES, 4, 4, 1),
    (False, DeleteMeshOption.ALL_NODES, 32, 48, 16),
    (False, DeleteMeshOption.ALL_FACE_CIRCUMCENTERS, 32, 48, 16),
    (False, DeleteMeshOption.ALL_COMPLETE_FACES, 36, 60, 25),
]


@pytest.mark.parametrize(
    "invert_deletion, delete_option, exp_nodes, exp_edges, exp_faces",
    cases_delete_mesh2d_small_polygon,
)
def test_delete_mesh2d_small_polygon(
    meshkernel_with_mesh2d: MeshKernel,
    invert_deletion: bool,
    delete_option: DeleteMeshOption,
    exp_nodes: int,
    exp_edges: int,
    exp_faces: int,
):
    """Test `delete_mesh2d` by deleting a polygon from a 6x6 mesh2d.

    30--31--32--33--34--35
    |   |   |   |   |   |
    24--25--26--27--28--29
    |   | * |   | * |   |
    18--19--20--21--22--23
    |   |   |   |   |   |
    12--13--14--15--16--17
    |   | * |   | * |   |
    6---7---8---9---10--11
    |   |   |   |   |   |
    0---1---2---3---4---5

    """
    mk = meshkernel_with_mesh2d(6, 6)

    # Polygon around nodes 14, 15, 21 & 20 (through the face circum centers)
    x_coordinates = np.array([1.5, 3.5, 3.5, 1.5, 1.5], dtype=np.double)
    y_coordinates = np.array([1.5, 1.5, 3.5, 3.5, 1.5], dtype=np.double)

    geometry_list = GeometryList(x_coordinates, y_coordinates)

    mk.delete_mesh2d(geometry_list, delete_option, invert_deletion)
    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == exp_nodes
    assert mesh2d.edge_x.size == exp_edges
    assert mesh2d.face_x.size == exp_faces


cases_delete_mesh2d_empty_polygon = [(False, 0, 0, 0), (True, 25, 40, 16)]


@pytest.mark.parametrize(
    "invert_deletion, exp_nodes, exp_edges, exp_faces",
    cases_delete_mesh2d_empty_polygon,
)
def test_delete_mesh2d_empty_polygon(
    meshkernel_with_mesh2d: MeshKernel,
    invert_deletion: bool,
    exp_nodes: int,
    exp_edges: int,
    exp_faces: int,
):
    """Test `delete_mesh2d` by deleting a an empty polygon from a 5x5 mesh2d.

    20--21--22--23--24
    |   |   |   |   |
    15--16--17--18--19
    |   |   |   |   |
    10--11--12--13--14
    |   |   |   |   |
    5---6---7---8---9
    |   |   |   |   |
    0---1---2---3---4

    """
    mk = meshkernel_with_mesh2d(5, 5)

    x_coordinates = np.empty(0, dtype=np.double)
    y_coordinates = np.empty(0, dtype=np.double)

    geometry_list = GeometryList(x_coordinates, y_coordinates)
    delete_option = DeleteMeshOption.ALL_NODES

    mk.delete_mesh2d(geometry_list, delete_option, invert_deletion)
    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == exp_nodes
    assert mesh2d.edge_x.size == exp_edges
    assert mesh2d.face_x.size == exp_faces


cases_get_hanging_edges_mesh2d = [
    (
        np.array([0.0, 1.0, 1.0, 0.0], dtype=np.double),  # node_x
        np.array([0.0, 0.0, 1.0, 1.0], dtype=np.double),  # node_y
        np.array([0, 1, 1, 3, 2, 3, 2, 0], dtype=np.int32),  # edge_nodes
        np.array([], dtype=np.int32),  # expected
    ),
    (
        np.array([0.0, 1.0, 1.0, 0.0, 0.0], dtype=np.double),  # node_x
        np.array([0.0, 0.0, 1.0, 1.0, 2.0], dtype=np.double),  # node_y
        np.array([0, 1, 1, 3, 2, 3, 2, 0, 3, 4], dtype=np.int32),  # edge_nodes
        np.array([4], dtype=np.int32),  # expected
    ),
    (
        np.array([0.0, 1.0, 1.0, 0.0, 0.0, 2.0], dtype=np.double),  # node_x
        np.array([0.0, 0.0, 1.0, 1.0, 2.0, 1.0], dtype=np.double),  # node_y
        np.array([0, 1, 1, 3, 2, 3, 2, 0, 3, 4, 2, 5], dtype=np.int32),  # edge_nodes
        np.array([4, 5], dtype=np.int32),  # expected
    ),
]


@pytest.mark.parametrize(
    "node_x, node_y, edge_nodes, expected", cases_get_hanging_edges_mesh2d
)
def test_get_hanging_edges_mesh2d(
    node_x: np.ndarray, node_y: np.ndarray, edge_nodes: np.ndarray, expected: int
):
    """Tests `get_hanging_edges_mesh2d` by comparing the returned hanging edges with the expected ones
    4*
    |
    3---2---5*
    |   |
    0---1
    """

    mk = MeshKernel()

    mesh2d = Mesh2d(node_x, node_y, edge_nodes)

    mk.set_mesh2d(mesh2d)

    result = mk.get_hanging_edges_mesh2d()

    assert_array_equal(result, expected)


def test_delete_hanging_edges_mesh2d():
    """Tests `delete_hanging_edges_mesh2d` by deleting 2 hanging edges in a simple Mesh2d
    4*
    |
    3---2---5*
    |   |
    0---1
    """

    mk = MeshKernel()

    node_x = np.array([0.0, 1.0, 1.0, 0.0, 0.0, 2.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 1.0, 1.0, 2.0, 1.0], dtype=np.double)
    edge_nodes = np.array([0, 1, 1, 2, 2, 3, 3, 0, 3, 4, 2, 5], dtype=np.int32)

    mesh2d = Mesh2d(node_x, node_y, edge_nodes)

    mk.set_mesh2d(mesh2d)

    mk.delete_hanging_edges_mesh2d()

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 4
    assert mesh2d.edge_x.size == 4
    assert mesh2d.face_x.size == 1


def test_make_mesh_from_polygon_mesh2d():
    """Tests `make_mesh_from_polygon_mesh2d` by creating a mesh2d from a simple hexagon."""

    mk = MeshKernel()

    #   5__4
    #  /    \
    # 0      3
    #  \1__2/
    x_coordinates = np.array([0.0, 0.5, 1.5, 2.0, 1.5, 0.5, 0.0], dtype=np.double)
    y_coordinates = np.array([1.0, 0.0, 0.0, 1.0, 2.0, 2.0, 1.0], dtype=np.double)
    polygon = GeometryList(x_coordinates, y_coordinates)

    mk.make_mesh_from_polygon_mesh2d(polygon)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 7
    assert mesh2d.edge_x.size == 12
    assert mesh2d.face_x.size == 6


def test_make_mesh_from_samples_mesh2d():
    """Tests `make_mesh_from_samples_mesh2d` by creating a mesh2d from six sample points."""

    mk = MeshKernel()

    #  5  4
    # 0    3
    #  1  2
    x_coordinates = np.array([0.0, 0.5, 1.5, 2.0, 1.5, 0.5, 0.0], dtype=np.double)
    y_coordinates = np.array([1.0, 0.0, 0.0, 1.0, 2.0, 2.0, 1.0], dtype=np.double)
    polygon = GeometryList(x_coordinates, y_coordinates)

    mk.make_mesh_from_samples_mesh2d(polygon)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 6
    assert mesh2d.edge_x.size == 9
    assert mesh2d.face_x.size == 4


cases_refine_polygon = [
    (0, 0, 30.0, 9),
    (0, 1, 30.0, 6),
    (0, 2, 30.0, 7),
    (0, 3, 30.0, 8),
    (0, 4, 30.0, 9),
    (0, 0, 20.0, 13),
    (0, 1, 20.0, 7),
    (0, 2, 20.0, 9),
    (0, 3, 20.0, 11),
    (0, 4, 20.0, 13),
]


@pytest.mark.parametrize("start, end, length, exp_nodes", cases_refine_polygon)
def test_refine_polygon(start: int, end: int, length: float, exp_nodes: int):
    """Tests `refine_polygon` by refining a simple polygon."""

    mk = MeshKernel()

    # 3---2
    # |   |
    # 0---1
    x_coordinates = np.array([0.0, 60.0, 60.0, 0.0, 0.0], dtype=np.double)
    y_coordinates = np.array([0.0, 0.0, 60.0, 60.0, 0.0], dtype=np.double)
    polygon = GeometryList(x_coordinates, y_coordinates)

    geom = mk.refine_polygon(polygon, start, end, length)

    assert geom.x_coordinates.size == exp_nodes


cases_refine_based_on_samples_mesh2d = [
    # (0.5, 1, 25, 40, 16),
    # (0.5, 2, 9, 12, 4),
]


@pytest.mark.parametrize(
    "min_face_size, refinement_type, exp_nodes, exp_edges, exp_faces",
    cases_refine_based_on_samples_mesh2d,
)
def test_refine_based_on_samples_mesh2d(
    meshkernel_with_mesh2d: MeshKernel,
    min_face_size: float,
    refinement_type: RefinementType,
    exp_nodes: int,
    exp_edges: int,
    exp_faces: int,
):
    """Tests `refine_based_on_samples_mesh2d` with a simple 3x3 mesh.

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2
    """
    mk = meshkernel_with_mesh2d(3, 3)

    x_coordinates = np.array([0.5, 0.5, 1.5, 1.5], dtype=np.double)
    y_coordinates = np.array([0.5, 1.5, 1.5, 0.5], dtype=np.double)
    values = np.array([2, 2, 2, 2], dtype=np.double)
    samples = GeometryList(x_coordinates, y_coordinates, values)

    refinement_params = MeshRefinementParameters(
        False, False, min_face_size, refinement_type, False, False, 1
    )

    mk.refine_based_on_samples_mesh2d(samples, refinement_params)

    mesdh2d = mk.get_mesh2d()

    assert mesdh2d.node_x.size == exp_nodes
    assert mesdh2d.edge_x.size == exp_edges
    assert mesdh2d.face_x.size == exp_faces


cases_refine_based_on_polygon_mesh2d = [
    (1, 25, 40, 16),
    (2, 81, 144, 64),
    (3, 289, 544, 256),
]


@pytest.mark.parametrize(
    "max_iterations, exp_nodes, exp_edges, exp_faces",
    cases_refine_based_on_polygon_mesh2d,
)
def test_refine_based_on_polygon_mesh2d(
    meshkernel_with_mesh2d: MeshKernel,
    max_iterations: int,
    exp_nodes: int,
    exp_edges: int,
    exp_faces: int,
):
    """Tests `refine_based_on_polygon_mesh2d` with a simple 3x3 mesh.

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2
    """

    mk = meshkernel_with_mesh2d(3, 3)

    x_coordinates = np.array([0.0, 0.0, 2.0, 2.0, 0.0], dtype=np.double)
    y_coordinates = np.array([0.0, 2.0, 2.0, 0.0, 0.0], dtype=np.double)
    polygon = GeometryList(x_coordinates, y_coordinates)

    refinement_params = MeshRefinementParameters(
        True, False, 0.5, 1, False, False, max_iterations
    )

    mk.refine_based_on_polygon_mesh2d(polygon, refinement_params)

    mesdh2d = mk.get_mesh2d()

    assert mesdh2d.node_x.size == exp_nodes
    assert mesdh2d.edge_x.size == exp_edges
    assert mesdh2d.face_x.size == exp_faces


def test_get_mesh_boundaries_as_polygons_mesh2d(meshkernel_with_mesh2d: MeshKernel):
    """Tests `get_mesh_boundaries_as_polygons_mesh2d` by checking if the resulted boundary is as expected"""

    mk = meshkernel_with_mesh2d(3, 3)

    mesh_boundary = mk.get_mesh_boundaries_as_polygons_mesh2d()
    assert_array_equal(
        mesh_boundary.x_coordinates,
        np.array([0.0, 0.0, 0.0, 1.0, 2.0, 2.0, 2.0, 1.0, 0.0], dtype=np.double),
    )
    assert_array_equal(
        mesh_boundary.y_coordinates,
        np.array([0.0, 1.0, 2.0, 2.0, 2.0, 1.0, 0.0, 0.0, 0.0], dtype=np.double),
    )


cases_merge_nodes_mesh2d = [(1e-2, 4), (1e-4, 5)]


@pytest.mark.parametrize("merging_distance, number_of_nodes", cases_merge_nodes_mesh2d)
def test_merge_nodes_mesh2d(merging_distance: float, number_of_nodes: int):
    """Test if `merge_nodes_mesh2d` reduces the number of close nodes

    4---3
    |   |
    01--2
    """
    mk = MeshKernel()

    # Set up mesh
    edge_nodes = np.array([0, 1, 1, 2, 2, 3, 3, 4, 4, 0], dtype=np.int32)
    node_x = np.array([0.0, 1e-3, 1.0, 1.0, 0.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 0.0, 1.0, 1.0], dtype=np.double)
    input_mesh2d = Mesh2d(node_x, node_y, edge_nodes)
    mk.set_mesh2d(input_mesh2d)

    # Define polygon where we want to merge
    x_coordinates = np.array([-1.0, 2.0, 2.0, -1.0, -1.0], dtype=np.double)
    y_coordinates = np.array([-1.0, -1.0, 2.0, 2.0, -1.0], dtype=np.double)
    geometry_list = GeometryList(x_coordinates, y_coordinates)

    mk.merge_nodes_mesh2d(geometry_list, merging_distance)

    output_mesh2d = mk.get_mesh2d()

    assert output_mesh2d.node_x.size == number_of_nodes


cases_merge_two_nodes_mesh2d = [(0, 1, 4), (4, 5, 4), (0, 4, 3)]


@pytest.mark.parametrize(
    "first_node, second_node, num_faces", cases_merge_two_nodes_mesh2d
)
def test_merge_two_nodes_mesh2d(
    meshkernel_with_mesh2d: MeshKernel,
    first_node: int,
    second_node: int,
    num_faces: int,
):
    """Tests `merge_two_nodes_mesh2d` by checking if two selected nodes are properly merged

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2
    """

    mk = meshkernel_with_mesh2d(3, 3)

    mk.merge_two_nodes_mesh2d(first_node, second_node)

    output_mesh2d = mk.get_mesh2d()

    assert output_mesh2d.node_x.size == 8
    assert output_mesh2d.face_x.size == num_faces


cases_get_points_in_polygon = [
    (
        # Select all
        np.array([0.0, 3.0, 3.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 3.0, 3.0, 0.0]),
        np.array([1.0, 1.0, 1.0, 1.0, 1.0]),
    ),
    (
        # Select right half
        np.array([1.5, 3.0, 3.0, 1.5, 1.5]),
        np.array([0.0, 0.0, 3.0, 3.0, 0.0]),
        np.array([0.0, 1.0, 1.0, 0.0, 0.0]),
    ),
    (
        # Select bottom-right
        np.array([1.5, 3.0, 3.0, 1.5, 1.5]),
        np.array([0.0, 0.0, 1.5, 1.5, 0.0]),
        np.array([0.0, 1.0, 0.0, 0.0, 0.0]),
    ),
    (
        # Select top half
        np.array([0.0, 3.0, 3.0, 0.0, 0.0]),
        np.array([1.5, 1.5, 3.0, 3.0, 1.5]),
        np.array([0.0, 0.0, 1.0, 1.0, 0.0]),
    ),
    (
        # Select top-left
        np.array([0.0, 1.5, 1.5, 0.0, 0.0]),
        np.array([1.5, 1.5, 3.0, 3.0, 1.5]),
        np.array([0.0, 0.0, 0.0, 1.0, 0.0]),
    ),
]


@pytest.mark.parametrize(
    "selecting_x, selecting_y, exp_values",
    cases_get_points_in_polygon,
)
def test_get_points_in_polygon(
    selecting_x: np.array, selecting_y: np.array, exp_values: np.array
):
    """Tests `get_points_in_polygon` with a simple polygon and various selecting polygons."""

    selecting_polygon = GeometryList(selecting_x, selecting_y)

    x_coordinates = np.array([1.0, 2.0, 2.0, 1.0, 1.0], dtype=np.double)
    y_coordinates = np.array([1.0, 1.0, 2.0, 2.0, 1.0], dtype=np.double)
    selected_polygon = GeometryList(x_coordinates, y_coordinates)

    mk = MeshKernel()

    selection = mk.get_points_in_polygon(selecting_polygon, selected_polygon)

    assert_array_equal(selection.values, exp_values)


def test_count_obtuse_triangles_mesh2d():
    r"""Tests `_count_obtuse_triangles_mesh2d` on a 3x3 mesh with two obtuse triangles.

    6---7---8
    | /   \ |
    3---4---5
    | \   / |
    0---1---2

    """
    mk = MeshKernel()

    # Mesh with obtuse triangles (4, 5, 7 and 1, 5, 4)
    node_x = np.array([0.0, 1.0, 2.0, 0.0, 1.5, 2.0, 0.0, 1.0, 2.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0], dtype=np.double)
    edge_nodes = np.array(
        [
            0,
            1,
            1,
            2,
            3,
            4,
            4,
            5,
            6,
            7,
            7,
            8,
            0,
            3,
            1,
            4,
            2,
            5,
            3,
            6,
            4,
            7,
            5,
            8,
            1,
            3,
            1,
            5,
            3,
            7,
            5,
            7,
        ],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    n_obtuse_triangles = mk._count_obtuse_triangles_mesh2d()

    assert n_obtuse_triangles == 2


def test_get_obtuse_triangles_mass_centers_mesh2d():
    r"""Tests `get_obtuse_triangles_mass_centers_mesh2d` on a 3x3 mesh with two obtuse triangles.

    6---7---8
    | /   \ |
    3---4---5
    | \   / |
    0---1---2

    """
    mk = MeshKernel()

    # Mesh with obtuse triangles (4, 5, 7 and 1, 5, 4)
    node_x = np.array([0.0, 1.0, 2.0, 0.0, 1.5, 2.0, 0.0, 1.0, 2.0], dtype=np.double)
    node_y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0], dtype=np.double)
    edge_nodes = np.array(
        [
            0,
            1,
            1,
            2,
            3,
            4,
            4,
            5,
            6,
            7,
            7,
            8,
            0,
            3,
            1,
            4,
            2,
            5,
            3,
            6,
            4,
            7,
            5,
            8,
            1,
            3,
            1,
            5,
            3,
            7,
            5,
            7,
        ],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    obtuse_triangles = mk.get_obtuse_triangles_mass_centers_mesh2d()

    assert obtuse_triangles.x_coordinates.size == 2

    assert obtuse_triangles.x_coordinates[0] == 1.5
    assert obtuse_triangles.y_coordinates[0] == approx(0.666, 0.01)

    assert obtuse_triangles.x_coordinates[1] == 1.5
    assert obtuse_triangles.y_coordinates[1] == approx(1.333, 0.01)


cases_count_small_flow_edge_centers_mesh2d = [(0.9, 0), (1.0, 0), (1.1, 4)]


@pytest.mark.parametrize(
    "threshold, exp_int", cases_count_small_flow_edge_centers_mesh2d
)
def test_count_small_flow_edge_centers_mesh2d(threshold: float, exp_int: int):
    """Tests `_count_small_flow_edge_centers_mesh2d` with a simple 3x3 mesh with 4 small flow edges.

    6---7---8
    | 11|-12|
    3-|-4-|-5
    | 9-|-10|
    0---1---2
    """

    mk = MeshKernel()

    node_x = np.array(
        [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.5, 1.5, 0.5, 1.5],
        dtype=np.double,
    )
    node_y = np.array(
        [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 0.5, 0.5, 1.5, 1.5],
        dtype=np.double,
    )
    edge_nodes = np.array(
        [
            0,
            1,
            1,
            2,
            3,
            4,
            4,
            5,
            6,
            7,
            7,
            8,
            0,
            3,
            1,
            4,
            2,
            5,
            3,
            6,
            4,
            7,
            5,
            8,
            9,
            10,
            11,
            12,
            9,
            11,
            10,
            12,
        ],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    n_small_flow_edges = mk._count_small_flow_edge_centers_mesh2d(threshold)

    assert n_small_flow_edges == exp_int


def test_get_small_flow_edge_centers_mesh2d():
    """Tests `get_small_flow_edge_centers_mesh2d` with a simple 3x3 mesh with 4 small flow edges.

    6---7---8
    | 11|-12|
    3-|-4-|-5
    | 9-|-10|
    0---1---2
    """

    mk = MeshKernel()

    node_x = np.array(
        [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.5, 1.5, 0.5, 1.5],
        dtype=np.double,
    )
    node_y = np.array(
        [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 0.5, 0.5, 1.5, 1.5],
        dtype=np.double,
    )
    edge_nodes = np.array(
        [
            0,
            1,
            1,
            2,
            3,
            4,
            4,
            5,
            6,
            7,
            7,
            8,
            0,
            3,
            1,
            4,
            2,
            5,
            3,
            6,
            4,
            7,
            5,
            8,
            9,
            10,
            11,
            12,
            9,
            11,
            10,
            12,
        ],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    small_flow_edge_centers = mk.get_small_flow_edge_centers_mesh2d(1.1)

    assert small_flow_edge_centers.x_coordinates.size == 4

    assert small_flow_edge_centers.x_coordinates[0] == 0.5
    assert small_flow_edge_centers.y_coordinates[0] == 1.0
    assert small_flow_edge_centers.x_coordinates[1] == 1.5
    assert small_flow_edge_centers.y_coordinates[1] == 1.0
    assert small_flow_edge_centers.x_coordinates[2] == 1.0
    assert small_flow_edge_centers.y_coordinates[2] == 0.5
    assert small_flow_edge_centers.x_coordinates[3] == 1.0
    assert small_flow_edge_centers.y_coordinates[3] == 1.5


def test_delete_small_flow_edges_and_small_triangles_mesh2d_delete_small_flow_edges():
    r"""Tests `get_small_flow_edge_centers_mesh2d` with a simple mesh with one small flow link.

    3---4---5
    | 6-|-7 |
    0---1---2
    """

    mk = MeshKernel()

    node_x = np.array(
        [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 0.5, 1.5],
        dtype=np.double,
    )
    node_y = np.array(
        [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5, 0.5],
        dtype=np.double,
    )
    edge_nodes = np.array(
        [0, 1, 1, 2, 3, 4, 4, 5, 0, 3, 1, 4, 2, 5, 6, 7],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    mk.delete_small_flow_edges_and_small_triangles_mesh2d(1.1, 0.01)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 8
    assert mesh2d.edge_x.size == 7
    assert mesh2d.face_x.size == 1


def test_delete_small_flow_edges_and_small_triangles_mesh2d_delete_small_triangles():
    r"""Tests `get_small_flow_edge_centers_mesh2d` with a simple mesh with one small triangle.

    3---4---5\
    |   |   | 6
    0---1---2/
    """

    mk = MeshKernel()

    node_x = np.array(
        [0.0, 1.0, 2.0, 0.0, 1.0, 2.0, 2.1],
        dtype=np.double,
    )
    node_y = np.array(
        [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5],
        dtype=np.double,
    )
    edge_nodes = np.array(
        [0, 1, 1, 2, 3, 4, 4, 5, 0, 3, 1, 4, 2, 5, 5, 6, 6, 2],
        dtype=np.int32,
    )

    mk.set_mesh2d(Mesh2d(node_x, node_y, edge_nodes))

    mk.delete_small_flow_edges_and_small_triangles_mesh2d(1.0, 0.01)

    mesh2d = mk.get_mesh2d()

    assert mesh2d.node_x.size == 7
    assert mesh2d.edge_x.size == 8
    assert mesh2d.face_x.size == 2


cases_nodes_in_polygons_mesh2d = [
    (np.array([1.5, 2.5, 2.5, 1.5, 1.5]), np.array([1.5, 1.5, 2.5, 2.5, 1.5]), True, 1),
    (
        np.array([1.5, 2.5, 2.5, 1.5, 1.5]),
        np.array([1.5, 1.5, 2.5, 2.5, 1.5]),
        False,
        8,
    ),
    (
        np.array([]),
        np.array([]),
        True,
        9,
    ),
]


@pytest.mark.parametrize(
    "x_coordinates, y_coordinates, inside, exp_num_nodes",
    cases_nodes_in_polygons_mesh2d,
)
def test_nodes_in_polygons_mesh2d(
    meshkernel_with_mesh2d: MeshKernel,
    x_coordinates: ndarray,
    y_coordinates: ndarray,
    inside: bool,
    exp_num_nodes: int,
):
    """Tests `nodes_in_polygons_mesh2d` by checking if it returns the correct number of nodes

    6---7---8
    |   |   |
    3---4---5
    |   |   |
    0---1---2
    """

    mk = meshkernel_with_mesh2d(3, 3)
    geometry_list = GeometryList(x_coordinates, y_coordinates)
    selected_nodes = mk.get_nodes_in_polygons_mesh2d(geometry_list, inside)

    assert selected_nodes.size == exp_num_nodes
