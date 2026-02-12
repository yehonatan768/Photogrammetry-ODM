Param(
  [Parameter(Mandatory=$true)]
  [string]$VideoPath
)

docker compose up -d --build
docker compose run --rm pipeline python -m src.cli run --video $VideoPath
