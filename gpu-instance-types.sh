#!/bin/bash

# Get instance types with GPUs in eu-north-1
aws ec2 describe-instance-types \
    --filters "Name=instance-type,Values=g4*,g5*" \
    --region eu-north-1 \
    --query 'InstanceTypes[].[InstanceType, GpuInfo.Gpus[0].Count]' \
    --output table

