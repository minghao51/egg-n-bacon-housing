# Use Alpine base image
FROM mambaorg/micromamba:latest

COPY environment.yml /tmp/env.yaml
# COPY environment.yml* .devcontainer/noop.txt /tmp/conda-tmp/
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/micromamba /usr/local/bin/mamba && ln -s /usr/bin/micromamba /usr/local/bin/conda
RUN alias mamba='micromamba' && alias conda='micromamba'
USER $MAMBA_USER



# Install bash and necessary dependencies
# RUN apk add --no-cache \
#     bash \
#     wget \
#     ca-certificates \
#     openssl && \
#     rm -rf /var/cache/apk/*

# # Download and install Mamba using Miniforge installer
# RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh && \
#     chmod +x /tmp/miniforge.sh && \
#     bash /tmp/miniforge.sh -b -p /opt/mamba && \
#     rm /tmp/miniforge.sh

# # Set environment variables for Mamba
# ENV PATH="/opt/mamba/bin:$PATH"

# # Set permissions for the Mamba directory
# RUN chown -R root:root /opt/mamba && \
#     chmod -R 755 /opt/mamba