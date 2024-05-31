import subprocess
import os
import multiprocessing as mp
import logging
import glob

# run minced and process results
def run_cctyper(workdir):
    mags = glob.glob(os.path.join(workdir, '*.bz2'))
    n_processed = 0

    for mag in mags:
        os.system('bunzip2 {}'.format(mag))
        unzipped_mag = mag.replace('.bz2', '')
        outdir = '.'.join(unzipped_mag.split('.')[:-1])
        if os.path.isfile(unzipped_mag):
            command = 'cctyper -t 1 --simplelog --skip_blast --no_plot {} {} > /dev/null 2>&1'.format(unzipped_mag, outdir)
            os.system(command)
            os.remove(unzipped_mag)
            n_processed += 1
    return n_processed

# log function
def make_log_result(results, len_parts):
    def log_result(retval):
        results.append(retval)
        if len(results) % 2 == 0:
            logging.info('{}/{} parts completed: {} MAGs analyzed'.format(len(results), len_parts, sum(results)))
    return log_result


if __name__ == '__main__':

    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level='INFO')
    ncores = 32
    base = '/shares/CIBIO-Storage/CM/scratch/users/matteo.ciciani/MetaRefSGB_Cas_mining/cctyper_1.8.0_Jan23/'

    releases = ['Dec19']#os.listdir(base)
    parts = [os.path.join(base, rel, part) for rel in releases for part in os.listdir(os.path.join(base, rel))]

    pool = mp.Pool(ncores)
    results = []
    logging.info('Running!')
    for part in parts:
        pool.apply_async(run_cctyper, args=[part],
            callback=make_log_result(results, len(parts)))
    pool.close()
    pool.join()
    logging.info('{} total genomes examined!'.format(sum(results)))
    logging.info('Done!')
