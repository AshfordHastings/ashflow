#!/bin/bash
export PGPASSWORD=password
psql -h localhost -U postgres -w password -d wiki -p 5434;