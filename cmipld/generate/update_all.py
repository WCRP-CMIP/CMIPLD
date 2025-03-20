#!/bin/python3

import glob, os, tqdm


def main():
    
    # do the equivalent of this, but only for the updated repos. 
    
    
    os.system('update_ctx')
    
    # os.system('update_schema')
    
    # os.system('update_issues')

    os.system('validjsonld')



    for i in tqdm.tqdm(glob.glob('src-data/*/')):

        os.system('ld2graph '+i)

