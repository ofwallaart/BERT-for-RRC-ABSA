#!/bin/bash

MODEL_TYPE=$1
BASELINE=$2
GPU=$3
FOLDER=$4

export CUDA_VISIBLE_DEVICES=${GPU}

export PYTHONPATH="${PYTHONPATH}:./"

MODEL_NAME=GroNLP/bert-base-dutch-cased
BATCH_SIZE=16
ACCUM=8

echo batch_size ${BATCH_SIZE} accum ${ACCUM}

OUTPUT_DIR=${FOLDER}/pt_${MODEL_TYPE}-${BASELINE}
TRAIN_FILE=${FOLDER}/domain_train.txt
EVAL_FILE=${FOLDER}/domain_dev.txt

mkdir -p ${OUTPUT_DIR}

python ../src/pt.py \
    --output_dir "${OUTPUT_DIR}" \
    --model_type "${MODEL_TYPE}" \
    --model_name_or_path ${MODEL_NAME} \
    --do_train \
    --train_data_file ${TRAIN_FILE} \
    --per_gpu_train_batch_size ${BATCH_SIZE} \
    --gradient_accumulation_steps ${ACCUM} \
    --do_eval \
    --eval_data_file ${EVAL_FILE} \
    --per_gpu_eval_batch_size ${BATCH_SIZE} \
    --evaluate_during_training \
    --do_lower_case \
    --mlm \
    --mlm_probability 0.15 \
    --block_size 512 \
    --learning_rate 5e-5 \
    --warmup_steps 0 \
    --adam_epsilon 1e-6 \
    --overwrite_output_dir \
    --seed 0 \
    --baseline ${BASELINE} \
    --save_steps 500 \
    --logging_steps 500 \
    --save_total_limit 1 \
    --num_train_epochs 6.0 \
    --fp16 \
    --fp16_opt_level O2 \
    2>&1 | tee ${OUTPUT_DIR}/train.log
