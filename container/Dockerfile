# CPU only. One case is one .tiff of 384 images with a 600 s limit; measured end to
# end from `docker run`, so container start-up and model loading are included, a case
# takes about 16 s on a laptop CPU and 26 s on the evaluation hardware.
# Dropping the GPU buys three things: the image falls from about 8 GB to about 1.5 GB
# (the limit is 10 GB, and image pull counts against the outer wall clock), there is no
# CUDA version risk, and there is no exposure to the T4 bf16 trap, so the instance type
# stops mattering.
FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8

RUN groupadd -r user && useradd -m --no-log-init -r -g user user
WORKDIR /opt/app

COPY --chown=user:user requirements.txt /opt/app/
# The CPU wheel for torch is about 200 MB against about 2.5 GB for the CUDA build,
# so the CPU index is selected explicitly.
RUN python -m pip install --no-cache-dir --no-color \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        -r /opt/app/requirements.txt \
 && rm -rf /root/.cache

COPY --chown=user:user resources /opt/app/resources
COPY --chown=user:user inference.py /opt/app/

USER user
ENTRYPOINT ["python", "inference.py"]
