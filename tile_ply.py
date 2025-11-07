from datetime import datetime
start = datetime.now()

import os
import json
import argparse

import numpy as np
import geopandas as gp
from shapely.geometry import Point

import pdal
from pointtorch import read


def tile_data(file_path, args):
    cmds = []

    # pdal commands as dictionaries
    read_in = {
        "type": "readers.ply",
        "filename": file_path
    }
    cmds.append(read_in)

    tile = {"type": "filters.splitter",
            "length": str(args.tile),
            "origin_x": "0",
            "origin_y": "0"}
    cmds.append(tile)

    rename_columns = {
        "type": "filters.ferry",
        "dimensions": "x=>X, y=>Y, z=>Z"
    }
    cmds.append(rename_columns)

    writer = {"type": "writers.ply",
              "storage_mode": "little endian",
              "filename": os.path.join(args.odir, f"{args.plot_code}tile_#.ply")
              }
    cmds.append(writer)

    # link commmands and pass to pdal
    JSON = json.dumps(cmds)

    pipeline = pdal.Pipeline(JSON)
    pipeline.execute()

    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--file-path', '-p', required=True, type=str, help='path to point cloud')
    parser.add_argument('--plot-code', type=str, default='', help='plot suffix')
    parser.add_argument('--odir', type=str, default='.', help='output directory')
    parser.add_argument('--tile', type=float, default=10, help='length of tile')
    parser.add_argument('--num-prcs', type=int, default=10, help='number of cores to use')
    parser.add_argument('--buffer', type=float, default=10., help='size of buffer')
    parser.add_argument('--verbose', action='store_true', help='print something')

    args = parser.parse_args()

    if args.buffer == 0: args.buffer = False

    point_cloud = read(args.file_path)
    xy_min = np.floor(point_cloud.xyz()[:, :2].min(axis=0))
    xy_max = np.floor(point_cloud.xyz()[:, :2].max(axis=0))

    # create tile db
    X, Y = np.meshgrid(np.arange(xy_min[0], xy_max[0], args.tile),
                       np.arange(xy_min[1], xy_max[1], args.tile))
    XY = np.vstack([X.flatten(), Y.flatten()]).T.astype(int)
    print("XY", XY)
    tiles = gp.GeoDataFrame(data=XY, columns=['x', 'y'], geometry=[Point(r[0], r[1]) for r in XY])
    
    tiles.loc[:, 'tile'] = range(len(tiles))
    tiles = tiles[['x', 'y', 'tile', 'geometry']]

    # write tile index
    tiles[['tile', 'x', 'y']].to_csv(os.path.join(args.odir, 'tile_index.dat'),  sep=' ', index=False, header=False)

    tile_data(args.file_path, args)

    print(f'runtime: {(datetime.now() - start).seconds}')
