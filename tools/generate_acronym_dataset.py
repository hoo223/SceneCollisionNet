import argparse
import os

import h5py
from tqdm import tqdm

from scenecollisionnet.utils import (
    MeshLoader,
    ProcessKillingExecutor,
    process_mesh,
)


def process_mesh_timeout(*args, **kwargs):
    pass


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate mesh dataset")
    parser.add_argument(
        "meshes_dir",
        type=str,
        help="path to the Shapenet mesh dataset directory",
    )
    parser.add_argument(
        "grasps_dir",
        type=str,
        help="path to ACRONYM grasp dataset directory of hdf5 files",
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="output dataset path",
    )

    args = parser.parse_args()
    mesh_dir = args.meshes_dir
    grasps_dir = args.grasps_dir
    out_dir = args.output_dir

    if not os.path.exists(mesh_dir):
        print("Input directory does not exist!")
    mesh_loader = MeshLoader(mesh_dir)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_ds_file = os.path.join(out_dir, "object_info.hdf5")

    inputs = []
    for f in tqdm(os.listdir(grasps_dir), desc="Generating Inputs"):
        mc, mk, ms = os.path.splitext(f)[0].split("_")
        try:
            in_path = mesh_loader.get_path(mk)
        except ValueError:
            continue
        out_path = os.path.join(
            out_dir,
            mc,
            os.path.splitext(os.path.basename(in_path))[0] + ".obj",
        )
        inputs.append(
            (in_path, out_path, float(ms), os.path.join(grasps_dir, f))
        )

    executor = ProcessKillingExecutor(max_workers=8)
    generator = executor.map(
        process_mesh,
        inputs[6500:],
        timeout=120,
        callback_timeout=process_mesh_timeout,
    )
    
    with h5py.File(out_ds_file, "a") as f:
        if "meshes" not in f:
            f.create_group("meshes")

        categories = {}
        if "categories" not in f:
            f.create_group("categories")

        for mesh_info in tqdm(
            generator, total=len(inputs), desc="Processing Meshes"
        ):
            if mesh_info is not None:
                mk, minfo = mesh_info # mesh name, mesh info
                if mk not in f["meshes"]:
                    f["meshes"].create_group(mk)
                for key in minfo:
                    if key in f["meshes"][mk]:
                        del f["meshes"][mk][key]
                    f["meshes"][mk][key] = minfo[key] # path, scale, category, stps, probs, grasps

                if minfo["category"] not in categories:
                    categories[minfo["category"]] = [mk.encode('utf8')] # string 저장 시 utf8로 인코딩하지 않으면 에러 발생
                elif mk not in categories[minfo["category"]]:
                    categories[minfo["category"]].append(mk.encode('utf8')) # string 저장 시 utf8로 인코딩하지 않으면 에러 발생

                category = minfo["category"]
                if category in f["categories"]:
                    del f["categories"][category]
                f["categories"][category] = categories[category]
