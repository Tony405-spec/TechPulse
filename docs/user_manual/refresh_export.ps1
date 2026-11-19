$path=(Resolve-Path 'docs/user_manual/TechPulse_User_Training_Manual.docx').Path
$workingPath=Join-Path (Split-Path $path -Parent) '.TechPulse_User_Training_Manual_working.docx'
Copy-Item -LiteralPath $path -Destination $workingPath -Force
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
$doc=$word.Documents.Open($workingPath,$false,$false)
$doc.Repaginate()
$doc.Fields.Update() | Out-Null
foreach($name in @('TOC 1','TOC 2','TOC 3')){
  try { $style=$doc.Styles.Item($name); $style.Font.Name='Times New Roman'; $style.Font.Size=10; $style.Font.Color=0 } catch { Write-Output "STYLE NOT FOUND: $name" }
}
foreach($name in @('Index 1','Index 2','Index Heading')){
  try { $style=$doc.Styles.Item($name); $style.Font.Name='Times New Roman'; $style.Font.Size=11; $style.Font.Color=0 } catch { Write-Output "STYLE NOT FOUND: $name" }
}
foreach($toc in $doc.TablesOfContents){$toc.Update() | Out-Null}
$doc.Fields.Update() | Out-Null
foreach($story in $doc.StoryRanges){
  $range=$story
  while($null -ne $range){
    $range.Font.Name='Times New Roman'
    $range.Font.Color=0
    $range=$range.NextStoryRange
  }
}
$pages=$doc.ComputeStatistics(2)
Write-Output "DOCX pages $pages; paragraphs $($doc.Paragraphs.Count); inline images $($doc.InlineShapes.Count); fields $($doc.Fields.Count)"
$doc.Save()
$out=[System.IO.Path]::ChangeExtension($path,'.pdf')
$doc.ExportAsFixedFormat($out,17)
$doc.Close($false)
$word.Quit()
Copy-Item -LiteralPath $workingPath -Destination $path -Force
Remove-Item -LiteralPath $workingPath -Force
Write-Output "PDF $out"
