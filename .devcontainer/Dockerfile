# Use a lightweight base image
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Set up non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install dependencies
RUN apt-get update && \
    apt-get install -y build-essential --no-install-recommends make \
                        ca-certificates \
                        git \
                        libssl-dev \
                        zlib1g-dev \
                        libbz2-dev \
                        libreadline-dev \
                        libsqlite3-dev \
                        wget \
                        curl \
                        llvm \
                        libncurses5-dev \
                        xz-utils \
                        tk-dev \
                        libxml2-dev \
                        libxmlsec1-dev \
                        libffi-dev \
                        liblzma-dev &&\
                        apt-get clean && \
                        rm -rf /var/lib/apt/lists/*

# Install Mamba using the Miniconda installer
RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh && \
    bash /tmp/miniforge.sh -b -p /opt/mamba && \
    rm /tmp/miniforge.sh && \
    chown -R root:root /opt/mamba && \
    chmod -R 755 /opt/mamba

# Initialize Mamba environment
ENV PATH="/opt/mamba/bin:${PATH}"

# Set up the conda environment using mamba
COPY environment.yml* .devcontainer/noop.txt /tmp/conda-tmp/
RUN if [ -f "/tmp/conda-tmp/environment.yml" ]; then umask 0002 && /opt/mamba/bin/mamba env create -f /tmp/conda-tmp/environment.yml; fi \
    && rm -rf /tmp/conda-tmp

# Set appropriate folder permissions
RUN chown -R root:root /opt/mamba && chmod -R 755 /opt/mamba


# FROM mcr.microsoft.com/devcontainers/miniconda:0-3

# # Copy environment.yml (if found) to a temp location so we update the environment. Also
# # copy "noop.txt" so the COPY instruction does not fail if no environment.yml exists.

# RUN conda install -n base -c conda-forge mamba=2.0.1
# COPY environment.yml* .devcontainer/noop.txt /tmp/conda-tmp/
# RUN if [ -f "/tmp/conda-tmp/environment.yml" ]; then umask 0002 && /opt/conda/bin/mamba env create -f /tmp/conda-tmp/environment.yml; fi \
#     && rm -rf /tmp/conda-tmp

# FROM mcr.microsoft.com/devcontainers/miniconda:0-3
# #devcontainers/base:debian
# # FROM mcr.microsoft.com/devcontainers/base:jammy 

# # ARG DEBIAN_FRONTEND=noninteractive
# # ARG USER=vscode

# # RUN DEBIAN_FRONTEND=noninteractive \
# #     && apt-get update \ 
# #     && apt-get install -y build-essential --no-install-recommends make \
# #         ca-certificates \
# #         git \
# #         libssl-dev \
# #         zlib1g-dev \
# #         libbz2-dev \
# #         libreadline-dev \
# #         libsqlite3-dev \
# #         wget \
# #         curl \
# #         llvm \
# #         libncurses5-dev \
# #         xz-utils \
# #         tk-dev \
# #         libxml2-dev \
# #         libxmlsec1-dev \
# #         libffi-dev \
# #         liblzma-dev

# # # Python and poetry installation
# # USER $USER
# # ARG HOME="/home/$USER"
# # ARG PYTHON_VERSION=3.11
# # # ARG PYTHON_VERSION=3.10

# # ENV PYENV_ROOT="${HOME}/.pyenv"
# # ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${HOME}/.local/bin:$PATH"

# # RUN echo "done 0" \
# #     && curl https://pyenv.run | bash \
# #     && echo "done 1" \
# #     && pyenv install ${PYTHON_VERSION} \
# #     && echo "done 2" \
# #     && pyenv global ${PYTHON_VERSION} \
# #     && echo "done 3" \
# #     && curl -sSL https://install.python-poetry.org | python3 - \
# #     && poetry config virtualenvs.in-project true

# RUN conda install -n base -c conda-forge mamba
# COPY environment.yml* .devcontainer/noop.txt /tmp/conda-tmp/
# RUN if [ -f "/tmp/conda-tmp/environment.yml" ]; then umask 0002 && /opt/conda/bin/mamba env create -f /tmp/conda-tmp/environment.yml; fi \
#         && rm -rf /tmp/conda-tmp