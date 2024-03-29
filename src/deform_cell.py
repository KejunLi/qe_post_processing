#!/usr/bin/env python3
import numpy as np
import sys
import os
from scipy.optimize import curve_fit
from read_qeout import qe_out
from read_qein import qe_in

class strain_and_deform_cell(object):
    """
    =---------------------------------------------------------------------------
    +   1. Constructor
    +   Input:
    +   cell_parameters (cell parameters)
    +   atomic_pos_cryst (atomic positions)
    =---------------------------------------------------------------------------
    +   2. Method unaxial_strain(self, strain, theta)
    +   Input:
    +   strain (strain applied to cell parameters in x-axis by default)
    +   theta: (rotation angle in degree between x-axis and symmetry axis, 
    +   e.g. C2 axis)
    +
    +   Attributes: none
    +
    +   return(new_cell_parameters)
    =---------------------------------------------------------------------------
    +   3. Method gaussian_wrinkle(self, amp, std, peak)
    +   Input:
    +   amp (amplitude of the gaussian function, angstrom)
    +   std (standard deviation of the gaussian function, angstrom)
    +   peak (center of the peak of the gaussian function, angstrom)
    +   theta (rotation angle in radian between x-axis and symmetry axis, 
    +   e.g. C2 axis)
    +
    +   Attributes: none
    +
    +   return(atomic_pos_cart)
    =---------------------------------------------------------------------------
    """
    def __init__(self, cell_parameters=None, atomic_pos_cryst=None):
        self._cell_parameters = cell_parameters
        self.cell_parameters = cell_parameters
        self._inv_cell_parameters = np.linalg.inv(self._cell_parameters)
        self._atomic_pos_cryst = atomic_pos_cryst
        self.atomic_pos_cryst = atomic_pos_cryst
        self.nat = atomic_pos_cryst.shape[0]

        # call dynamic methods
        self._atomic_pos_cart = np.matmul(atomic_pos_cryst, self._cell_parameters)
        self.rotate()
    
    def rotate(self, alpha=0, beta=0, gamma=0):
        """
        =-----------------------------------------------------------------------
        +   Let atomic positions in fractional crystal coordinates be A, 
        +   cell parameters be C, rotational matrix be R.
        +
        +   The atomic positions in angstrom A_1 = AC.
        +   By rotation, (A_2)^T = R(A_1)^T = R(C^T)(A^T)
        +   Therefore, new cell parameters after rotation is CR^T, and the atomic
        +   positions in cell parameters are the same as they are.
        +   Here the rotation is only allowed in perpendicular to 2D plane.
        +
        +   Step 1. alpha: rotation along x axis
        +   Step 2. beta: rotation along y axis
        +   Step 3. gamma: rotation along z axis
        =-----------------------------------------------------------------------
        """
        # convert to radian from degree
        alpha = alpha / 180.0 * np.pi 
        beta = beta / 180.0 * np.pi 
        gamma = gamma / 180.0 * np.pi 
        # rotation matrix along x
        rot_x = np.matrix(
            [
                [1, 0, 0], 
                [0, np.cos(alpha), -np.sin(alpha)],
                [0, np.sin(alpha), np.cos(alpha)]
            ]
        )
        # rotation matrix along y
        rot_y = np.matrix(
            [
                [np.cos(beta), 0, np.sin(beta)], 
                [0, 1, 0],
                [-np.sin(alpha), 0, np.cos(alpha)]
            ]
        )
        # rotation matrix along z
        rot_z = np.matrix(
            [
                [np.cos(gamma), -np.sin(gamma), 0], 
                [np.sin(gamma), np.cos(gamma), 0],
                [0, 0, 1]
            ]
        )
        # first rotate along x, then y, finally z
        rotation_mat = np.matmul(rot_z, np.matmul(rot_y, rot_x))

        self.cell_parameters = np.matmul(
            self._cell_parameters, np.transpose(rotation_mat)
        )

    
    def homogeneous_strain(self, strain=0):
        """
        =-----------------------------------------------------------------------
        +   Only change the cell parameters
        +
        +   Let atomic positions in fractional crystal coordinates be A, 
        +   cell parameters be C, and uniaxial strain matrix be S.
        +
        +   The atomic positions in angstrom A_1 = AC.
        +   By applying strain, (A_2)^T = S(A_1)^T = SC^TA^T.
        +   Here we have A_2 = ACS^T .
        +   Therefore, the cell parameters after applying strain to the symmetry 
        +   axis is C_1 = CS^T.
        +   Here the rotation is only allowed in perpendicular to 2D plane.
        =-----------------------------------------------------------------------
        """
        strain_mat = np.matrix(
            [
                [1 + strain, 0, 0], 
                [0, 1 + strain, 0], 
                [0, 0, 1]
            ]
        )
        self.cell_parameters = np.matmul(
            self._cell_parameters, np.transpose(strain_mat)
        )


    def uniaxial_strain(self, strain=0, theta=0):
        """
        =-----------------------------------------------------------------------
        +   The uniaxial strain is applied along x-axis
        +
        +   Let atomic positions in fractional crystal coordinates be A, 
        +   cell parameters be C, rotational matrix be R, 
        +   and uniaxial strain matrix be S.
        +
        +   The atomic positions in angstrom A_1 = AC.
        +   By rotation, (A_2)^T = R(A_1)^T; 
        +   by applying strain, (A_3)^T = S(A_2)^T.
        +   After applying the uniaxial to the designated direction, we need to 
        +   rerotate the atomic positions back to the original, 
        +   so (A_4)^T = R^{-1}(A_3)^T = R^{-1}SR(AC)^T.
        +   Here we have A_4 = AC(R^{-1}SR)^T = A[C(R^{-1}SR)^T].
        +   Therefore, the cell parameters after applying strain to the symmetry 
        +   axis is C_1 = C(R^{-1}SR)^T.
        +   Here the rotation is only allowed in perpendicular to 2D plane.
        =-----------------------------------------------------------------------
        """
        theta = theta / 180.0 * np.pi # convert to radian from degree
        strain_mat = np.matrix(
            [
                [1 + strain, 0, 0], 
                [0, 1, 0], 
                [0, 0, 1]
            ]
        )
        rotation_mat = np.matrix(
            [
                [np.cos(theta), -np.sin(theta), 0], 
                [np.sin(theta), np.cos(theta), 0],
                [0, 0, 1]
            ]
        )
        inv_rotation_mat = np.linalg.inv(rotation_mat)
        strain_rot_mat = np.matmul(strain_mat, rotation_mat)
        strain_rot_mat = np.matmul(inv_rotation_mat, strain_rot_mat)
        self.cell_parameters = np.matmul(
            self._cell_parameters, np.transpose(strain_rot_mat)
        )

    def gaussian(self, amp, std, peak, x):
        x = np.asarray(x)
        y = amp * np.exp(-0.5*(x-peak)**2/std**2)
        return y
    
    def curvature_gaussian(self, amp, std, t=np.linspace(-10, 10, 1000)):
        """
        =-----------------------------------------------------------------------
        +   This method is used for estimating the curvature of gaussian 
        +   x(t) = t
        +   y(t) = amp * exp(-1/2 * (t^2) / std^2)
        =-----------------------------------------------------------------------
        """
        dx_dt = 1
        d2x_dt2 = 0
        dy_dt = -t / std**2 * amp * np.exp(-0.5 * t**2 / std**2)
        d2y_dt2 = (
            (t**2 / std**4 - 1 / std**2) * amp * np.exp(-0.5 * t**2 / std**2)
        )
        curvature = np.abs(
            (d2x_dt2*dy_dt - dx_dt*d2y_dt2)/(dx_dt**2 + dy_dt**2)**1.5
        )
        curvature = round(np.amax(curvature), 3)
        print("The largest curvature = {} A^-1\n".format(curvature))
    
    def gaussian_wrinkle(self, amp=2.0, std=2.0, peak=[0, 0], theta=0):
        """
        =-----------------------------------------------------------------------
        +   Transform the 2D supercell by creating a gaussian-shaped wrinkle
        +   along x-axis
        +   z += gaussian(amp, std, peak_y, y)
        +
        +   Define atomic positions in cartisian coordinate as A, rotation 
        +   matrix as R.
        +   Rotate matrix A by RA^T, then transform  the supercell, finally
        +   rotate back the transformed supercell R^{-1}RA^T.
        =-----------------------------------------------------------------------
        """
        theta = theta / 180.0 * np.pi # convert to radian from degree
        rotation_mat = np.matrix(
            [
                [np.cos(theta), -np.sin(theta), 0], 
                [np.sin(theta), np.cos(theta), 0],
                [0, 0, 1]
            ]
        )
        inv_rotation_mat = np.linalg.inv(rotation_mat)
        atomic_pos_cart = self._atomic_pos_cart
        atomic_pos_cart = np.matmul(atomic_pos_cart, np.transpose(rotation_mat))
        atomic_pos_cart[:, 2] += self.gaussian(
            amp, std, peak[1], atomic_pos_cart[:, 1]
        )
        atomic_pos_cart = np.matmul(
            atomic_pos_cart, np.transpose(inv_rotation_mat)
        )
        self.atomic_pos_cryst = np.matmul(
            atomic_pos_cart, self._inv_cell_parameters
        )
        return self.atomic_pos_cryst
    
    def gaussian_bump(self, amp=1.0, std=1.0, peak=[0, 0]):
        """
        =-----------------------------------------------------------------------
        +   Transform the 2D supercell by creating a gaussian-shaped wrinkle
        +   along x-axis
        +   z += gaussian(amp, std, peak_y, y)
        =-----------------------------------------------------------------------
        """
        atomic_pos_cart = self._atomic_pos_cart
        atomic_pos_cart[:, 2] += (
            self.gaussian(amp, std, peak[0], atomic_pos_cart[:, 0]) 
            * self.gaussian(amp, std, peak[1], atomic_pos_cart[:, 1])
            / amp
        )
        self.atomic_pos_cryst = np.matmul(
            atomic_pos_cart, self._inv_cell_parameters
        )
        return(self.atomic_pos_cryst)

    # def parameterize_plane(
    #     self, xy: np.ndarray, 
    #     amp: float, std: float, peak: tuple,
    #     a: float, b: float
    # ):
    #     z = (
    #         amp 
    #         * exp(-0.5 * (a*(xy - peak)[:, 0] + b*(xy-peak)[:, 1])**2 / std**2)
    #     )
    #     return z
    
    # def best_vals_of_parameters(self, xy: np.ndarray, z:np.ndarray):
    #     init_vals = [1.0, 1.0, [1.0, 1.0], 1.0, 1.0]
    #     best_vals, covar = curve_fit(parameterize_plane, xy, z, p0=init_vals)
    #     print(
    #         "\rbest_vals: amp={}, std={}, peak={}, a={}, b={}\n"
    #         .format(
    #             best_vals[0], best_vals[1], best_vals[2], best_vals[3],
    #             best_vals[4]
    #         )
    #     )
    #     return best_vals

    # def actual_curvature(self, )
    

if __name__ == "__main__":
    cwd = os.getcwd()
    if sys.argv[1].endswith("out"):
        qe = qe_out(os.path.join(cwd, sys.argv[1]), verbosity=False)
        sdc = strain_and_deform_cell(
            cell_parameters=qe.cell_parameters, 
            atomic_pos_cryst=qe.atomic_pos_cryst
        )
        sdc.rotate(theta=float(sys.argv[2]))
        cellpara = sdc.cell_parameters
    elif sys.argv[1].endswith("in"):
        qe = qe_in(os.path.join(cwd, sys.argv[1]))
        sdc = strain_and_deform_cell(
            cell_parameters=qe.cell_parameters, 
            atomic_pos_cryst=qe.atomic_pos_cryst
        )
        sdc.rotate(theta=float(sys.argv[2]))
        cellpara = sdc.cell_parameters
    print(cellpara)

    

