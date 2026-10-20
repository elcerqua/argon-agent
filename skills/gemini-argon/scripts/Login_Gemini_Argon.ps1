# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
$ErrorActionPreference = 'Stop'
$argonPython = (Get-Command python -ErrorAction Stop).Source
$argonWrapper = Join-Path $PSScriptRoot 'Gemini_Argon.py'
Write-Host "Gemini: completa il login Google in Antigravity CLI con l'account del tuo piano Google AI."
Write-Host 'Non vengono inviati file di progetto. Dopo il login puoi chiudere la CLI.'
& $argonPython $argonWrapper login
