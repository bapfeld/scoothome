import os, argparse
from collections import Counter
import pandas as pd

def main(dir_path, dat_path, calculate_missing, out_path):
    event_list = []
    f_list = [x for x in os.listdir(dir_path) if x.endswith('txt')]
    f_list = [os.path.join(dir_path, x) for x in f_list]
    for f in f_list:
        with open(f, 'r') as f_in:
            event_list.extend(f_in.readlines())
    if calculate_missing:
        pass
    else:
        counts = pd.DataFrame.from_dict(Counter(event_list),
                                        orient='index',
                                        columns=['n']).reset_index()
        counts['area'] = counts['index'].str.extract(r'^(.*?)--')
        counts['time'] = counts['index'].str.extract(r'--(.*?)$')

    # write out again
    counts.to_csv(out_path,
                  columns=['area', 'time', 'n'],
                  index=False)    

def initialize_params():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--dir_path',
            help="Path to directory storing all the files",
            required=True,
        )
        parser.add_argument(
            '--dat_path',
            help="Path to the corresponding data file to figure out missing values",
            required=False,
        )
        parser.add_argument(
            '--calculate_missing',
            help="Should the code attempt to fill in missing values with 0? Defaults to false.",
            required=False,
            action="store_true"
        )
        parser.add_argument(
            '--out_path',
            help="Path to where to save final file",
            required=True,
        )
        return parser.parse_args()
    
if __name__ == "__main__":
    args = initialize_params()
    main(os.path.expanduser(args.dir_path),
         os.path.expanduser(args.dat_path),
         args.calculate_missing,
         os.path.expanduser(args.out_path))
