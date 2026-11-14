#!/usr/bin/env bash
# Jednorazova priprava tortury pro test instalace rpraxe: Docker Engine + Compose plugin.
# Spustit jako root (nebo sudo bash tenhle-soubor) NA TORTURE.
#
# Proc ne /get.docker.com: Linux Mint nema vlastni distribuci v Docker repositarich
# a skript by selhal na neznamem codename. Misto toho se pouzije Ubuntu repositak
# podle UBUNTU_CODENAME z /etc/os-release (Mint 22.x = noble).
set -euo pipefail

UBU=$(. /etc/os-release && echo "${UBUNTU_CODENAME:-noble}")
echo "== cilova distribuce pro Docker repositak: ubuntu/$UBU =="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
if [ ! -s /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL "https://download.docker.com/linux/ubuntu/gpg" \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $UBU stable
EOF

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

# pridat tebe do skupiny docker, at "docker compose" funguje bez sudo
U="${SUDO_USER:-}"
if [ -n "$U" ] && [ "$U" != root ]; then
  usermod -aG docker "$U" && echo "skupina docker pridana uzivateli $U"
else
  echo "PRIDEJ SI RUCNE: sudo usermod -aG docker <jmeno>"
fi

docker --version
docker compose version
echo "== HOTOVO: odhlas se a znova prihlas (kvuli skupine docker), pak over: docker ps =="
