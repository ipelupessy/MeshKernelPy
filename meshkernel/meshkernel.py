import logging
import platform
from ctypes import CDLL, byref, c_char_p, c_double, c_int, c_size_t
from enum import IntEnum, unique
from pathlib import Path
from typing import Callable

import numpy as np
from numpy import ndarray
from numpy.ctypeslib import as_ctypes

from meshkernel.c_structures import (
    CContacts,
    CGeometryList,
    CMesh1d,
    CMesh2d,
    CMeshRefinementParameters,
    COrthogonalizationParameters,
)
from meshkernel.errors import InputError, MeshKernelError
from meshkernel.py_structures import (
    AveragingMethod,
    Contacts,
    DeleteMeshOption,
    GeometryList,
    Mesh1d,
    Mesh2d,
    Mesh2dLocation,
    MeshRefinementParameters,
    OrthogonalizationParameters,
    ProjectToLandBoundaryOption,
)
from meshkernel.version import __version__

logger = logging.getLogger(__name__)


@unique
class Status(IntEnum):
    SUCCESS = 0
    EXCEPTION = 1
    INVALID_GEOMETRY = 2


class MeshKernel:
    """This class is the entry point for interacting with the MeshKernel library"""

    def __init__(self, is_geographic: bool = False):
        """Constructor of MeshKernel

        Args:
            is_geographic (bool, optional): Whether the mesh is cartesian (False) or spherical (True).
                                            Default is `False`.

        Raises:
            OSError: This gets raised in case MeshKernel is used within an unsupported OS.
        """

        # Determine OS
        system = platform.system()
        if system == "Windows":
            lib_path = Path(__file__).parent / "MeshKernelApi.dll"
        elif system == "Linux":
            lib_path = Path(__file__).parent / "libMeshKernelApi.so"
        elif system == "Darwin":
            lib_path = Path(__file__).parent / "libMeshKernelApi.dylib"
        else:
            raise OSError(f"Unsupported operating system: {system}")

        self.lib = CDLL(str(lib_path))
        self._allocate_state(is_geographic)

    def __del__(self):
        self._deallocate_state()

    def _allocate_state(self, is_geographic: bool) -> None:
        """Creates a new empty mesh.

        Args:
            is_geographic (bool): Cartesian (False) or spherical (True) mesh.
        """

        self._meshkernelid = c_int()
        self._execute_function(
            self.lib.mkernel_allocate_state,
            c_int(is_geographic),
            byref(self._meshkernelid),
        )

    def _deallocate_state(self) -> None:
        """
        Deallocate mesh state.

        This method is called by the destructor and
        should never be called manually
        """

        self._execute_function(
            self.lib.mkernel_deallocate_state,
            self._meshkernelid,
        )

    def mesh2d_set(self, mesh2d: Mesh2d) -> None:
        """Sets the two-dimensional mesh state of the MeshKernel.

        Please note that this involves a copy of the data.

        Args:
            mesh2d (Mesh2d): The input data used for setting the state.
        """
        c_mesh2d = CMesh2d.from_mesh2d(mesh2d)

        self._execute_function(
            self.lib.mkernel_mesh2d_set, self._meshkernelid, byref(c_mesh2d)
        )

    def mesh2d_get(self) -> Mesh2d:
        """Gets the two-dimensional mesh state from the MeshKernel.

        Please note that this involves a copy of the data.

        Returns:
            Mesh2d: A copy of the two-dimensional mesh state.
        """

        c_mesh2d = self._mesh2d_get_dimensions()
        mesh2d = c_mesh2d.allocate_memory()
        self._execute_function(
            self.lib.mkernel_mesh2d_get_data, self._meshkernelid, byref(c_mesh2d)
        )

        return mesh2d

    def _mesh2d_get_dimensions(self) -> CMesh2d:
        """For internal use only.

        Gets the Mesh2d dimensions.
        The integer parameters of the Mesh2D struct are set to the corresponding dimensions.
        The pointers must be set to correctly sized memory before passing the struct to `mesh2d_get`.

        Returns:
            Mesh2d: The Mesh2d dimensions.
        """
        c_mesh2d = CMesh2d()
        self._execute_function(
            self.lib.mkernel_mesh2d_get_dimensions, self._meshkernelid, byref(c_mesh2d)
        )
        return c_mesh2d

    def mesh2d_delete(
        self,
        geometry_list: GeometryList,
        delete_option: DeleteMeshOption,
        invert_deletion: bool,
    ) -> None:
        """Deletes a mesh in a polygon using several options.

        Args:
            geometry_list (GeometryList): The GeometryList describing the polygon where to perform the operation.
            delete_option (DeleteMeshOption): The option describing the strategy to delete the mesh.
            invert_deletion (bool): Whether or not to invert the deletion.
        """

        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)

        self._execute_function(
            self.lib.mkernel_mesh2d_delete,
            self._meshkernelid,
            byref(c_geometry_list),
            c_int(delete_option),
            c_int(invert_deletion),
        )

    def mesh2d_insert_edge(self, start_node: int, end_node: int) -> int:
        """Insert a new mesh2d edge connecting two given nodes.

        Args:
            start_node (int): The index of the first node.
            end_node (int): The index of the second node.

        Returns:
            int: The index of the new edge.
        """

        edge_index = c_int()
        self._execute_function(
            self.lib.mkernel_mesh2d_insert_edge,
            self._meshkernelid,
            c_int(start_node),
            c_int(end_node),
            byref(edge_index),
        )

        return edge_index.value

    def mesh2d_insert_node(self, x: float, y: float) -> int:
        """Insert a new node at the specified coordinates

        Args:
            x (float): The x-coordinate of the new node.
            y (float): The y-coordinate of the new node.

        Returns:
            int: The index of the new node.
        """

        index = c_int()

        self._execute_function(
            self.lib.mkernel_mesh2d_insert_node,
            self._meshkernelid,
            c_double(x),
            c_double(y),
            byref(index),
        )
        return index.value

    def mesh2d_delete_node(self, node_index: int) -> None:
        """Deletes a Mesh2d node with the given `index`.

        Args:
            node_index (int): The index of the node to be deleted.

        Raises:
            InputError: Raised when `node_index` is smaller than 0.
        """

        if node_index < 0:
            raise InputError("node_index needs to be a positive integer")

        self._execute_function(
            self.lib.mkernel_mesh2d_delete_node, self._meshkernelid, c_int(node_index)
        )

    def mesh2d_move_node(self, x: float, y: float, node_index: int) -> None:
        """Moves a Mesh2d node with the given `index` to the point position.

        Args:
            x (float): The x-coordinate of the new position of the node.
            y (float): The y-coordinate of the new position of the node.
            node_index (int): The index of the node to be moved.

        Raises:
            InputError: Raised when `node_index` is smaller than 0.
        """

        if node_index < 0:
            raise InputError("node_index needs to be a positive integer")

        self._execute_function(
            self.lib.mkernel_mesh2d_move_node,
            self._meshkernelid,
            c_double(x),
            c_double(y),
            c_int(node_index),
        )

    def mesh2d_delete_edge(self, x_coordinate: float, y_coordinate: float) -> None:
        """Deletes the closest mesh2d edge to a point.
        The coordinates of the edge middle points are used for calculating the distances to the point.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.
        """

        self._execute_function(
            self.lib.mkernel_mesh2d_delete_edge,
            self._meshkernelid,
            c_double(x_coordinate),
            c_double(y_coordinate),
        )

    def mesh2d_get_edge(self, x: float, y: float) -> int:
        """Gets the closest mesh2d edge to a point.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.

        Returns:
            int: The index of the edge.
        """

        index = c_int()

        self._execute_function(
            self.lib.mkernel_mesh2d_get_edge,
            self._meshkernelid,
            c_double(x),
            c_double(y),
            byref(index),
        )

        return index.value

    def mesh2d_get_node_index(self, x: float, y: float, search_radius: float) -> int:
        """Finds the node closest to a point within a given search radius.

        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.
            search_radius (float): The search radius.

        Returns:
            int: The index of node.
        """

        index = c_int()

        self._execute_function(
            self.lib.mkernel_mesh2d_get_node_index,
            self._meshkernelid,
            c_double(x),
            c_double(y),
            c_double(search_radius),
            byref(index),
        )

        return index.value

    def mesh2d_get_hanging_edges(self) -> ndarray:
        """Gets the indices of hanging edges. A hanging edge is an edge where one of the two nodes is not connected.

        Returns:
            ndarray:  The integer array describing the indices of the hanging edges.
        """

        # Get number of hanging edges
        number_hanging_edges = self._mesh2d_count_hanging_edges()

        # Get hanging edges
        hanging_edges = np.empty(number_hanging_edges, dtype=np.int32)
        c_hanging_edges = np.ctypeslib.as_ctypes(hanging_edges)
        self._execute_function(
            self.lib.mkernel_mesh2d_get_hanging_edges,
            self._meshkernelid,
            byref(c_hanging_edges),
        )

        return hanging_edges

    def _mesh2d_count_hanging_edges(self) -> int:
        """For internal use only.

        Count the number of hanging edges in a mesh2d.
        An hanging edge is an edge where one of the two nodes is not connected.

        Returns:
            int: The number of hanging edges.
        """
        c_number_hanging_edges = c_int()
        self._execute_function(
            self.lib.mkernel_mesh2d_count_hanging_edges,
            self._meshkernelid,
            byref(c_number_hanging_edges),
        )
        return c_number_hanging_edges.value

    def mesh2d_delete_hanging_edges(self) -> None:
        """Delete the hanging edges in the Mesh2d.
        A hanging edge is an edge where one of the two nodes is not connected.
        """

        self._execute_function(
            self.lib.mkernel_mesh2d_delete_hanging_edges, self._meshkernelid
        )

    def mesh2d_make_mesh_from_polygon(self, polygon: GeometryList) -> None:
        """Generates a triangular mesh2d within a polygon. The size of the triangles is determined from the length of
        the polygon edges.

        Args:
            polygon (GeometryList): The polygon.
        """

        c_geometry_list = CGeometryList.from_geometrylist(polygon)

        self._execute_function(
            self.lib.mkernel_mesh2d_make_mesh_from_polygon,
            self._meshkernelid,
            byref(c_geometry_list),
        )

    def mesh2d_make_mesh_from_samples(self, sample_points: GeometryList) -> None:
        """Makes a triangular mesh from a set of samples, triangulating the sample points.

        Args:
            sample_points (GeometryList): The sample points.
        """

        c_geometry_list = CGeometryList.from_geometrylist(sample_points)

        self._execute_function(
            self.lib.mkernel_mesh2d_make_mesh_from_samples,
            self._meshkernelid,
            byref(c_geometry_list),
        )

    def polygon_refine(
        self,
        polygon: GeometryList,
        first_node: int,
        second_node: int,
        target_edge_length: float,
    ) -> GeometryList:
        """Refines the polygon perimeter between two nodes. This interval is refined to achieve a target edge length.

        Args:
            polygon (GeometryList): The input polygon to refine.
            first_node (int): The first index of the refinement interval.
            second_node (int): The second index of the refinement interval.
            target_edge_length (float): The target interval edge length.

        Returns:
            int: The refined polygon.
        """
        c_polygon = CGeometryList.from_geometrylist(polygon)
        c_n_polygon_nodes = c_int()

        self._execute_function(
            self.lib.mkernel_polygon_count_refine,
            self._meshkernelid,
            byref(c_polygon),
            c_int(first_node),
            c_int(second_node),
            c_double(target_edge_length),
            byref(c_n_polygon_nodes),
        )

        n_coordinates = c_n_polygon_nodes.value

        x_coordinates = np.empty(n_coordinates, dtype=np.double)
        y_coordinates = np.empty(n_coordinates, dtype=np.double)
        refined_polygon = GeometryList(x_coordinates, y_coordinates)

        c_refined_polygon = CGeometryList.from_geometrylist(refined_polygon)

        self._execute_function(
            self.lib.mkernel_polygon_refine,
            self._meshkernelid,
            byref(c_polygon),
            c_int(first_node),
            c_int(second_node),
            c_double(target_edge_length),
            byref(c_refined_polygon),
        )

        return refined_polygon

    def mesh2d_refine_based_on_samples(
        self,
        samples: GeometryList,
        relative_search_radius: float,
        minimum_num_samples: int,
        mesh_refinement_params: MeshRefinementParameters,
    ) -> None:
        """Refines a mesh2d based on samples. Refinement is achieved by successive splits of the face edges.
        The number of successive splits is indicated by the sample value.
        For example:
        - a value of 0 means no split and hence no refinement;
        - a value of 1 means a single split (a quadrilateral face generates 4 faces);
        - a value of 2 two splits (a quadrilateral face generates 16 faces).

        Args:
            samples (GeometryList): The samples.
            relative_search_radius (float): The relative search radius relative to the face size,
                                            used for some interpolation algorithms.
            minimum_num_samples (int): The minimum number of samples used for some averaging algorithms.
            mesh_refinement_params (MeshRefinementParameters): The mesh refinement parameters.
        """

        c_samples = CGeometryList.from_geometrylist(samples)
        c_refinement_params = CMeshRefinementParameters.from_meshrefinementparameters(
            mesh_refinement_params
        )

        self._execute_function(
            self.lib.mkernel_mesh2d_refine_based_on_samples,
            self._meshkernelid,
            byref(c_samples),
            c_double(relative_search_radius),
            c_int(minimum_num_samples),
            byref(c_refinement_params),
        )

    def mesh2d_refine_based_on_polygon(
        self,
        polygon: GeometryList,
        mesh_refinement_params: MeshRefinementParameters,
    ) -> None:
        """Refines a mesh2d within a polygon. Refinement is achieved by splitting the edges contained in the polygon in two.

        Args:
            samples (GeometryList): The closed polygon.
            mesh_refinement_params (MeshRefinementParameters): The mesh refinement parameters.
        """

        c_polygon = CGeometryList.from_geometrylist(polygon)
        c_refinement_params = CMeshRefinementParameters.from_meshrefinementparameters(
            mesh_refinement_params
        )

        self._execute_function(
            self.lib.mkernel_mesh2d_refine_based_on_polygon,
            self._meshkernelid,
            byref(c_polygon),
            byref(c_refinement_params),
        )

    def polygon_get_included_points(
        self, selecting_polygon: GeometryList, selected_polygon: GeometryList
    ) -> GeometryList:
        """Selects the polygon points within another polygon.

        Args:
            selecting_polygon (GeometryList): The selection polygon.
            selected_polygon (GeometryList): The polygon of which to get the selected points.

        Returns:
            GeometryList: The selection result. The selected points are contained in the values array of the returned
                          GeometryList (0.0 not selected, 1.0 selected).
        """

        c_selecting_polygon = CGeometryList.from_geometrylist(selecting_polygon)
        c_selected_polygon = CGeometryList.from_geometrylist(selected_polygon)

        n_coordinates = selected_polygon.x_coordinates.size

        x_coordinates = np.empty(n_coordinates, dtype=np.double)
        y_coordinates = np.empty(n_coordinates, dtype=np.double)
        values = np.empty(n_coordinates, dtype=np.double)
        selection = GeometryList(x_coordinates, y_coordinates, values)

        c_selection = CGeometryList.from_geometrylist(selection)

        self._execute_function(
            self.lib.mkernel_polygon_get_included_points,
            self._meshkernelid,
            byref(c_selecting_polygon),
            byref(c_selected_polygon),
            byref(c_selection),
        )

        return selection

    def mesh2d_flip_edges(
        self,
        triangulation_required: bool,
        project_to_land_boundary_required: bool,
        selecting_polygon: GeometryList,
        land_boundaries: GeometryList,
    ):
        """Flips mesh2d edges to optimize the mesh smoothness.
        Nodes that are connected to more than six other nodes are typically enclosed by faces of highly non-uniform
        shape and wildly varying areas.

        Args:
            triangulation_required (bool): Whether to triangulate non-triangular cells.
            project_to_land_boundary_required (bool): Whether projection to land boundaries is required.
            selecting_polygon (GeometryList): The polygon where to perform the edge flipping.
            land_boundaries (GeometryList): The land boundaries to account for when flipping the edges.

        """

        c_selecting_polygon = CGeometryList.from_geometrylist(selecting_polygon)
        c_land_boundaries = CGeometryList.from_geometrylist(land_boundaries)

        self._execute_function(
            self.lib.mkernel_mesh2d_flip_edges,
            self._meshkernelid,
            c_int(triangulation_required),
            c_int(project_to_land_boundary_required),
            byref(c_selecting_polygon),
            byref(c_land_boundaries),
        )

    def _mesh2d_count_obtuse_triangles(self) -> int:
        """For internal use only.

        Gets the number of obtuse mesh2d triangles.
        Obtuse triangles are those having one angle larger than 90°.

        Returns:
            int: The number of obtuse triangles.
        """

        n_obtuse_triangles = c_int(0)

        self._execute_function(
            self.lib.mkernel_mesh2d_count_obtuse_triangles,
            self._meshkernelid,
            byref(n_obtuse_triangles),
        )

        return n_obtuse_triangles.value

    def mesh2d_get_obtuse_triangles_mass_centers(self) -> GeometryList:
        """Gets the mass centers of obtuse mesh2d triangles.
        Obtuse triangles are those having one angle larger than 90°.

        Returns:
            GeometryList: The geometry list with the mass center coordinates.
        """
        n_obtuse_triangles = self._mesh2d_count_obtuse_triangles()

        x_coordinates = np.empty(n_obtuse_triangles, dtype=np.double)
        y_coordinates = np.empty(n_obtuse_triangles, dtype=np.double)
        geometry_list = GeometryList(x_coordinates, y_coordinates)

        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)

        self._execute_function(
            self.lib.mkernel_mesh2d_get_obtuse_triangles_mass_centers,
            self._meshkernelid,
            byref(c_geometry_list),
        )

        return geometry_list

    def _mesh2d_count_small_flow_edge_centers(
        self, small_flow_edges_length_threshold: float
    ) -> int:
        """For internal use only.

        Counts the number of small mesh2d flow edges.
        The flow edges are the edges connecting face circumcenters.

        Args:
            small_flow_edges_length_threshold (float): The configurable length for detecting a small flow edge.

        Returns:
            int: The number of the small flow edges.
        """

        n_small_flow_edge_centers = c_int()
        self._execute_function(
            self.lib.mkernel_mesh2d_count_small_flow_edge_centers,
            self._meshkernelid,
            c_double(small_flow_edges_length_threshold),
            byref(n_small_flow_edge_centers),
        )

        return n_small_flow_edge_centers.value

    def mesh2d_get_small_flow_edge_centers(
        self, small_flow_edges_length_threshold: float
    ) -> GeometryList:
        """Gets the small mesh2d flow edges centers.
        The flow edges are the edges connecting face circumcenters.

        Args:
            small_flow_edges_length_threshold (float): The configurable length for detecting a small flow edge.

        Returns:
            int: The geometry list with the small flow edge center coordinates.
        """

        n_small_flow_edge_centers = self._mesh2d_count_small_flow_edge_centers(
            small_flow_edges_length_threshold
        )

        x_coordinates = np.empty(n_small_flow_edge_centers, dtype=np.double)
        y_coordinates = np.empty(n_small_flow_edge_centers, dtype=np.double)
        geometry_list = GeometryList(x_coordinates, y_coordinates)

        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)

        self._execute_function(
            self.lib.mkernel_mesh2d_get_small_flow_edge_centers,
            self._meshkernelid,
            c_double(small_flow_edges_length_threshold),
            byref(c_geometry_list),
        )

        return geometry_list

    def mesh2d_delete_small_flow_edges_and_small_triangles(
        self,
        small_flow_edges_length_threshold: float,
        min_fractional_area_triangles: float,
    ) -> None:
        """Deletes all small mesh2d flow edges and small triangles.
        The flow edges are the edges connecting faces circumcenters.

        Args:
            small_flow_edges_length_threshold (float): The configurable length for detecting a small flow edge.
            min_fractional_area_triangles (float): The ratio of the face area to the average area of neighboring
                                                   non-triangular faces. This parameter is used for determining whether
                                                   a triangular face is small.
        """

        self._execute_function(
            self.lib.mkernel_mesh2d_delete_small_flow_edges_and_small_triangles,
            self._meshkernelid,
            c_double(small_flow_edges_length_threshold),
            c_double(min_fractional_area_triangles),
        )

    def get_splines(
        self, geometry_list: GeometryList, number_of_points_between_nodes: int
    ) -> GeometryList:
        """Get the computed spline points between two corner nodes.

        Args:
            geometry_list (GeometryList): The input corner nodes of the splines.
            number_of_points_between_nodes (int): The number of spline points to generate between two corner nodes.

        Returns:
            GeometryList: The output spline.
        """

        # Allocate space for output
        original_number_of_coordinates = geometry_list.x_coordinates.size
        number_of_coordinates = (
            original_number_of_coordinates * number_of_points_between_nodes
            - number_of_points_between_nodes
            + original_number_of_coordinates
            + 1
        )
        x_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        y_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        values = np.empty(number_of_coordinates, dtype=np.double)
        geometry_list_out = GeometryList(x_coordinates, y_coordinates, values)

        # Convert to CGeometryList
        c_geometry_list_in = CGeometryList.from_geometrylist(geometry_list)
        c_geometry_list_out = CGeometryList.from_geometrylist(geometry_list_out)

        self._execute_function(
            self.lib.mkernel_get_splines,
            byref(c_geometry_list_in),
            byref(c_geometry_list_out),
            c_int(number_of_points_between_nodes),
        )

        return geometry_list_out

    def mesh2d_get_mesh_boundaries_as_polygons(self) -> GeometryList:
        """Retrieves the boundaries of a mesh as a series of separated polygons.

        For example, if a mesh has an single inner hole, two polygons will be generated,
        one for the inner boundary and one for the outer boundary.

        Returns:
            GeometryList: The output network boundary polygon.
        """

        # Get number of polygon nodes
        number_of_polygon_nodes = self._mesh2d_count_mesh_boundaries_as_polygons()

        # Create GeometryList instance
        x_coordinates = np.empty(number_of_polygon_nodes, dtype=np.double)
        y_coordinates = np.empty(number_of_polygon_nodes, dtype=np.double)
        geometry_list_out = GeometryList(x_coordinates, y_coordinates)

        # Get mesh boundary
        c_geometry_list_out = CGeometryList.from_geometrylist(geometry_list_out)
        self._execute_function(
            self.lib.mkernel_mesh2d_get_mesh_boundaries_as_polygons,
            self._meshkernelid,
            byref(c_geometry_list_out),
        )

        return geometry_list_out

    def _mesh2d_count_mesh_boundaries_as_polygons(self) -> int:
        """For internal use only.

        Counts the number of polygon nodes contained in the mesh boundary polygons
        computed in function mesh2d_get_mesh_boundaries_as_polygons.

        Returns:
            int: The number of polygon nodes.
        """
        number_of_polygon_nodes = c_int()
        self._execute_function(
            self.lib.mkernel_mesh2d_count_mesh_boundaries_as_polygons,
            self._meshkernelid,
            byref(number_of_polygon_nodes),
        )
        return number_of_polygon_nodes.value

    def mesh2d_merge_nodes(
        self, geometry_list: GeometryList, merging_distance: float
    ) -> None:
        """Merges the mesh2d nodes, effectively removing all small edges.

        Args:
            geometry_list (GeometryList): The polygon defining the area where the operation will be performed.
            geometry_list (float): The distance below which two nodes will be merged.
        """
        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)
        self._execute_function(
            self.lib.mkernel_mesh2d_merge_nodes,
            self._meshkernelid,
            byref(c_geometry_list),
            c_double(merging_distance),
        )

    def mesh2d_merge_two_nodes(self, first_node: int, second_node: int) -> None:
        """Merges `first_node` into `second_node`.

        Args:
            first_node (int): The index of the first node to merge.
            second_node (int): The index of the second node to merge.
        """

        self._execute_function(
            self.lib.mkernel_mesh2d_merge_two_nodes,
            self._meshkernelid,
            c_int(first_node),
            c_int(second_node),
        )

    def mesh2d_get_nodes_in_polygons(
        self, geometry_list: GeometryList, inside: bool
    ) -> ndarray:
        """Gets the indices of the mesh2d nodes selected with a polygon.

        Args:
            geometry_list (GeometryList): The input polygon.
            inside (bool): Selection of the nodes inside the polygon (True) or outside (False).

        Returns:
            ndarray: The integer array describing the selected nodes indices.
        """

        # Get number of mesh nodes
        number_of_mesh_nodes = self._mesh2d_count_nodes_in_polygons(
            geometry_list, inside
        )

        selected_nodes = np.empty(number_of_mesh_nodes, dtype=np.int32)
        c_selected_nodes = np.ctypeslib.as_ctypes(selected_nodes)
        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)

        # Get selected nodes
        self._execute_function(
            self.lib.mkernel_mesh2d_get_nodes_in_polygons,
            self._meshkernelid,
            byref(c_geometry_list),
            c_int(inside),
            c_selected_nodes,
        )

        return selected_nodes

    def _mesh2d_count_nodes_in_polygons(
        self, geometry_list: GeometryList, inside: int
    ) -> int:
        """For internal use only.

        Counts the number of selected mesh node indices.
        This function should be used by clients before `mesh2d_get_nodes_in_polygons`
        for allocating an integer array storing the selection results.

        Returns:
            int: The number of selected nodes
        """
        c_number_of_mesh_nodes = c_int()
        c_geometry_list = CGeometryList.from_geometrylist(geometry_list)

        # Get number of mesh nodes
        self._execute_function(
            self.lib.mkernel_mesh2d_count_nodes_in_polygons,
            self._meshkernelid,
            byref(c_geometry_list),
            c_int(inside),
            byref(c_number_of_mesh_nodes),
        )
        return c_number_of_mesh_nodes.value

    def mesh1d_set(self, mesh1d: Mesh1d) -> None:
        """Sets the one-dimensional mesh state of the MeshKernel.

        Please note that this involves a copy of the data.

        Args:
            mesh1d (Mesh1d): The input data used for setting the state.
        """

        c_mesh1d = CMesh1d.from_mesh1d(mesh1d)

        self._execute_function(
            self.lib.mkernel_mesh1d_set, self._meshkernelid, byref(c_mesh1d)
        )

    def mesh1d_get(self) -> Mesh1d:
        """Gets the one-dimensional mesh state from the MeshKernel.

        Please note that this involves a copy of the data.

        Returns:
            Mesh1d: A copy of the two-dimensional mesh state.
        """

        c_mesh1d = self._mesh1d_get_dimensions()

        mesh1d = c_mesh1d.allocate_memory()
        self._execute_function(
            self.lib.mkernel_mesh1d_get_data, self._meshkernelid, byref(c_mesh1d)
        )

        return mesh1d

    def _mesh1d_get_dimensions(self) -> CMesh1d:
        """For internal use only.

        Gets the Mesh1d dimensions.
        The integer parameters of the Mesh1D struct are set to the corresponding dimensions.
        The pointers must be set to correctly sized memory before passing the struct to `mesh1d_get`.

        Returns:
            CMesh1d: The CMesh1d with the set dimensions.
        """
        c_mesh1d = CMesh1d()
        self._execute_function(
            self.lib.mkernel_mesh1d_get_dimensions, self._meshkernelid, byref(c_mesh1d)
        )
        return c_mesh1d

    def _contacts_get_dimensions(self) -> CContacts:
        """For internal use only.

        Gets the Contacts dimensions.
        The integer parameters of the Contacts struct are set to the corresponding dimensions.
        The pointers must be set to correctly sized memory before passing the struct to `contacts_get`.

        Returns:
            CContacts: The Contacts with the set dimensions.
        """
        c_contacts = CContacts()

        self._execute_function(
            self.lib.mkernel_contacts_get_dimensions,
            self._meshkernelid,
            byref(c_contacts),
        )

        return c_contacts

    def contacts_get(self) -> Contacts:
        """Gets the Contacts between the Mesh1d and Mesh2d from the MeshKernel.

        Please note that this involves a copy of the data.

        Returns:
            Contacts: The contacts.
        """
        c_contacts = self._contacts_get_dimensions()

        contacts = c_contacts.allocate_memory()

        self._execute_function(
            self.lib.mkernel_contacts_get_data, self._meshkernelid, byref(c_contacts)
        )

        return contacts

    def contacts_compute_single(
        self, node_mask: ndarray, polygons: GeometryList
    ) -> None:
        """Computes Mesh1d-Mesh2d contacts, where each single Mesh1d node is connected to one Mesh2d face circumcenter.
        The boundary nodes of Mesh1d (those sharing only one Mesh1d edge) are not connected to any Mesh2d face.

        Args:
            node_mask (ndarray): A boolean array describing whether Mesh1d nodes should or
                                 should not be connected
            polygons (GeometryList): The polygons selecting the area where the contacts will be be generated.
        """

        node_mask_int = node_mask.astype(np.int32)
        c_node_mask = as_ctypes(node_mask_int)
        c_polygons = CGeometryList.from_geometrylist(polygons)

        self._execute_function(
            self.lib.mkernel_contacts_compute_single,
            self._meshkernelid,
            c_node_mask,
            byref(c_polygons),
        )

    def contacts_compute_multiple(self, node_mask: ndarray) -> None:
        """Computes Mesh1d-Mesh2d contacts, where a single Mesh1d node is connected to multiple Mesh2d face circumcenters.

        Args:
            node_mask (ndarray): A boolean array describing whether Mesh1d nodes should or
                                 should not be connected
        """

        node_mask_int = node_mask.astype(np.int32)
        c_node_mask = as_ctypes(node_mask_int)

        self._execute_function(
            self.lib.mkernel_contacts_compute_multiple,
            self._meshkernelid,
            c_node_mask,
        )

    def contacts_compute_with_polygons(
        self, node_mask: ndarray, polygons: GeometryList
    ) -> None:
        """Computes Mesh1d-Mesh2d contacts, where a Mesh2d face per polygon is connected to the closest Mesh1d node.

        Args:
            node_mask (ndarray): A boolean array describing whether Mesh1d nodes should or
                                 should not be connected
            polygons (GeometryList): The polygons in which the closest Mesh2d face to a Mesh1d node will be connected.

        """

        node_mask_int = node_mask.astype(np.int32)
        c_node_mask = as_ctypes(node_mask_int)
        c_polygons = CGeometryList.from_geometrylist(polygons)

        self._execute_function(
            self.lib.mkernel_contacts_compute_with_polygons,
            self._meshkernelid,
            c_node_mask,
            byref(c_polygons),
        )

    def contacts_compute_with_points(
        self, node_mask: ndarray, points: GeometryList
    ) -> None:
        """Computes Mesh1d-Mesh2d contacts, where Mesh1d nodes are connected to the Mesh2d face mass centers containing
        the input point.

        Args:
            node_mask (ndarray): A boolean array describing whether Mesh1d nodes should or
                                 should not be connected
            points (GeometryList): The points selecting the Mesh2d faces to connect.

        """
        node_mask_int = node_mask.astype(np.int32)
        c_node_mask = as_ctypes(node_mask_int)
        c_points = CGeometryList.from_geometrylist(points)

        self._execute_function(
            self.lib.mkernel_contacts_compute_with_points,
            self._meshkernelid,
            c_node_mask,
            byref(c_points),
        )

    def contacts_compute_boundary(
        self, node_mask: ndarray, polygons: GeometryList, search_radius: float
    ) -> None:
        """Computes Mesh1d-Mesh2d contacts, where Mesh1d nodes are connected to the closest Mesh2d faces at the boundary

        Args:
            node_mask (ndarray): A boolean array describing whether Mesh1d nodes should or
                                 should not be connected
            points (GeometryList): The points selecting the Mesh2d faces to connect.
            search_radius (float): The radius used for searching neighboring Mesh2d faces. If it is equal to the missing
                                   value double, the search radius will be calculated internally.

        """

        node_mask_int = node_mask.astype(np.int32)
        c_node_mask = as_ctypes(node_mask_int)
        c_polygons = CGeometryList.from_geometrylist(polygons)

        self._execute_function(
            self.lib.mkernel_contacts_compute_boundary,
            self._meshkernelid,
            c_node_mask,
            byref(c_polygons),
            c_double(search_radius),
        )

    def mesh2d_compute_orthogonalization(
        self,
        project_to_land_boundary_option: ProjectToLandBoundaryOption,
        orthogonalization_parameters: OrthogonalizationParameters,
        selecting_polygon: GeometryList,
        land_boundaries: GeometryList,
    ) -> None:
        """Orthogonalizes the Mesh2d.
        The function modifies the mesh for achieving orthogonality between the edges
        and the segments connecting the face circumcenters.
        The amount of orthogonality is traded against the mesh smoothing (in this case the equality of face areas).

        Args:
            project_to_land_boundary_option (ProjectToLandBoundaryOption): The option to determine how to snap to
                                                                           land boundaries.
            orthogonalization_parameters (OrthogonalizationParameters): The orthogonalization parameters.
            selecting_polygon (GeometryList): The polygon where to perform the orthogonalization.
            land_boundaries (GeometryList): The land boundaries to account for in the orthogonalization process.
        """

        c_orthogonalization_params = (
            COrthogonalizationParameters.from_orthogonalizationparameters(
                orthogonalization_parameters
            )
        )
        c_selecting_polygon = CGeometryList.from_geometrylist(selecting_polygon)
        c_land_boundaries = CGeometryList.from_geometrylist(land_boundaries)

        self._execute_function(
            self.lib.mkernel_mesh2d_compute_orthogonalization,
            self._meshkernelid,
            c_int(project_to_land_boundary_option),
            byref(c_orthogonalization_params),
            byref(c_selecting_polygon),
            byref(c_land_boundaries),
        )

    def mesh2d_get_orthogonality(self) -> GeometryList:
        """Gets the mesh orthogonality, expressed as the ratio between the edges and
        the segments connecting the face circumcenters.

        Returns:
            GeometryList: The geometry list with the orthogonality values of each edge.
        """

        number_of_coordinates = self._mesh2d_get_dimensions().num_edges

        x_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        y_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        values = np.empty(number_of_coordinates, dtype=np.double)
        geometry_list_out = GeometryList(x_coordinates, y_coordinates, values)

        c_geometry_list_out = CGeometryList.from_geometrylist(geometry_list_out)
        self._execute_function(
            self.lib.mkernel_mesh2d_get_orthogonality,
            self._meshkernelid,
            byref(c_geometry_list_out),
        )

        return geometry_list_out

    def mesh2d_get_smoothness(self):
        """Gets the smoothness, expressed as the ratio between the values of two neighboring faces areas.

        Returns:
            GeometryList: The geometry list with the smoothness values of each edge.
        """

        number_of_coordinates = self._mesh2d_get_dimensions().num_edges

        x_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        y_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        values = np.empty(number_of_coordinates, dtype=np.double)
        geometry_list_out = GeometryList(x_coordinates, y_coordinates, values)

        c_geometry_list_out = CGeometryList.from_geometrylist(geometry_list_out)
        self._execute_function(
            self.lib.mkernel_mesh2d_get_smoothness,
            self._meshkernelid,
            byref(c_geometry_list_out),
        )

        return geometry_list_out

    def _get_error(self) -> str:
        c_error_message = c_char_p()
        self.lib.mkernel_get_error(byref(c_error_message))
        return c_error_message.value.decode("ASCII")

    def mesh2d_triangulation_interpolation(
        self,
        samples: GeometryList,
        location_type: Mesh2dLocation,
    ) -> GeometryList:
        """Performs triangulation interpolation of samples.

        Args:
            samples (GeometryList): The samples to interpolate.
            location_type (Mesh2dLocation): The location type on which to interpolate.

        Returns:
            GeometryList: The interpolated samples.
        """
        c_samples = CGeometryList.from_geometrylist(samples)

        number_of_coordinates = c_samples.n_coordinates

        x_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        y_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        values = np.empty(number_of_coordinates, dtype=np.double)
        interpolated_samples = GeometryList(x_coordinates, y_coordinates, values)

        c_interpolated_samples = CGeometryList.from_geometrylist(interpolated_samples)

        self._execute_function(
            self.lib.mkernel_mesh2d_triangulation_interpolation,
            self._meshkernelid,
            byref(c_samples),
            c_int(location_type),
            byref(c_interpolated_samples),
        )

        return interpolated_samples

    def mesh2d_averaging_interpolation(
        self,
        samples: GeometryList,
        location_type: Mesh2dLocation,
        averaging_method: AveragingMethod,
        relative_search_size: float,
        min_samples: int,
    ) -> GeometryList:
        """Performs averaging interpolation of samples.

        Args:
            samples (GeometryList): The samples to interpolate.
            location_type (Mesh2dLocation): The location type on which to interpolate.
            averaging_method (AveragingMethod): The averaging method.
            relative_search_size (float): The relative search size.
            min_samples (int): The minimum number of samples used for some interpolation algorithms to perform
                               a valid interpolation.

        Returns:
            GeometryList: The interpolated samples.
        """
        c_samples = CGeometryList.from_geometrylist(samples)

        number_of_coordinates = c_samples.n_coordinates

        x_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        y_coordinates = np.empty(number_of_coordinates, dtype=np.double)
        values = np.empty(number_of_coordinates, dtype=np.double)
        interpolated_samples = GeometryList(x_coordinates, y_coordinates, values)

        c_interpolated_samples = CGeometryList.from_geometrylist(interpolated_samples)

        self._execute_function(
            self.lib.mkernel_mesh2d_averaging_interpolation,
            self._meshkernelid,
            byref(c_samples),
            c_int(location_type),
            c_int(averaging_method),
            c_double(relative_search_size),
            c_size_t(min_samples),
            byref(c_interpolated_samples),
        )

        return interpolated_samples

    def get_meshkernel_version(self) -> str:
        """Get the version of the underlying C++ MeshKernel library

        Returns:
            str: The version string
        """

        c_meshkernel_version = c_char_p()
        self.lib.mkernel_get_version(byref(c_meshkernel_version))
        return c_meshkernel_version.value.decode("ASCII")

    def get_meshkernelpy_version(self) -> str:
        """Get the version of this Python wrapper

        Returns:
            str: The version string
        """

        return __version__

    def _execute_function(self, function: Callable, *args):
        """Utility function to execute a C function of MeshKernel and checks its status.

        Args:
            function (Callable): The function which we want to call.
            args: Arguments which will be passed to `function`.

        Raises:
            MeshKernelError: This exception gets raised,
                             if the MeshKernel library reports an error.
        """
        if function(*args) != Status.SUCCESS:
            error_message = self._get_error()
            raise MeshKernelError(error_message)
