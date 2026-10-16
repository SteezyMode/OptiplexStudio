# OptiPlex Studio Desktop v3: additive layer over the working Wolf image.
# Build on the OptiPlex with: docker build -f docker/studio-desktop-v3.Dockerfile -t optiplex-studio-desktop:v3 .
# Never include SSH credentials in the image.
FROM optiplex-studio-desktop:v2

USER root
# Ubuntu 25.04 (Plucky) has reached EOL; use Ubuntu's historical mirror.
# This is a short-term compatibility workaround, not a maintained OS baseline.
RUN set -eu; \
    sed -i 's|http://archive.ubuntu.com/ubuntu/|http://old-releases.ubuntu.com/ubuntu/|g; s|http://security.ubuntu.com/ubuntu/|http://old-releases.ubuntu.com/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openssh-client; \
    rm -rf /var/lib/apt/lists/*

COPY studio/wolf_ai_workspace.py /opt/optiplex-studio/wolf_ai_workspace.py
COPY docker/optiplex-ai-workspace.desktop /usr/share/applications/optiplex-ai-workspace.desktop
RUN chmod 0755 /opt/optiplex-studio/wolf_ai_workspace.py && \
    chmod 0644 /usr/share/applications/optiplex-ai-workspace.desktop

# Wolf's entrypoint and session environment are inherited unchanged.
