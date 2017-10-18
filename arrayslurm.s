#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=5
#SBATCH --time=01:00:00
#SBATCH --mem=100GB
#SBATCH --job-name=jets-experiment
#SBATCH --mail-type=END
#SBATCH --mail-user=henrion@nyu.edu
#SBATCH --output=slurm_%j.out
##SBATCH --gres=gpu:1

module purge
SRCDIR=$HOME/jets
DATA_DIR=$SCRATCH/data/w-vs-qcd/pickles
cd $SRCDIR
source activate jets
model_type=5
COUNTER=$SLURM_ARRAY_TASK_ID
let 'SEED = COUNTER * 10000'
##printf 'python train.py --data_dir %s -m %s --seed %s -v -g 1 &\n' $DATA_DIR $model_type $SEED
##python train.py --data_dir $DATA_DIR -m $model_type --seed $SEED -g 1 &
python train.py -v -m 5 --data_dir $DATA_DIR -g 1 -e 2 -n 1000
disown %1
sleep 5

##./slurm_run.sh -d $DATA_DIR -m 5 -n 3
#########
##
