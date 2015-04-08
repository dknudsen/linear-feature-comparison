# linear-feature-comparison
Python tool re-write of ArcGIS built-in feature comparison geoprocessing tool
Created on: 2014-06-26 11:23:02.00000
Usage: Create_difference_records_for_two_feature_classes <inFC1> <inFC2> <inFieldMap> <inKeyField1> <inKeyField2> <outDiffRecords>
Description: 
A homegrown version of the feature comparison tool meant to address a few of its shortcomings.
One shortcoming, addressed in version 10.2 of ArcGIS, but not in version 10.0, is that the
maximum number of difference records written is 1500, even when the checkbox to continue comparison
is checked. Another significant shortcoming is that the two feature classes being compared must have
exactly the same key values; there cannot have been added or deleted records. Less important
shortcomings to be improved upon in this custom tool include a difference record format that is
hard to use, and the requirement that field names match exactly (this version allows field mapping).
