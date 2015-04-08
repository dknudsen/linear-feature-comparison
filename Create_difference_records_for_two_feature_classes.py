# ---------------------------------------------------------------------------
# Create_difference_records_for_two_feature_classes.py
# Created on: 2014-06-26 11:23:02.00000
# Usage: Create_difference_records_for_two_feature_classes <inFC1> <inFC2> <inFieldMap> <inKeyField1> <inKeyField2> <outDiffRecords>
# Description: 
# A homegrown version of the feature comparison tool meant to address a few of its shortcomings.
# One shortcoming, addressed in version 10.2 of ArcGIS, but not in version 10.0, is that the
# maximum number of difference records written is 1500, even when the checkbox to continue comparison
# is checked. Another significant shortcoming is that the two feature classes being compared must have
# exactly the same key values; there cannot have been added or deleted records. Less important
# shortcomings to be improved upon in this custom tool include a difference record format that is
# hard to use, and the requirement that field names match exactly (this version allows field mapping).
#
# 2014-12-22: Corrected code that hardcoded the object ID field names
# ---------------------------------------------------------------------------

# Import arcpy module
import arcpy, os, ctypes, locale, datetime
from ctypes.wintypes import MAX_PATH

arcpy.env.qualifiedFieldNames = False

# Script arguments
inFC1 = arcpy.GetParameterAsText(0)
if inFC1 == '#' or not inFC1:
    inFC1 = r"S:\HQ\Planning\DataResources\Workspace\CTPS\60616_MassDOT_Road_Inventory_Supplemental_Grant\GIS\Data\MassDOT_Planning\Planning_Development.sde\gisDevelopment.GISPLANNER.AddressDevelopment\gisDevelopment.GISPLANNER.MGIS_STREETS_BASE" # provide a default value if unspecified

inFC2 = arcpy.GetParameterAsText(1)
if inFC2 == '#' or not inFC2:
    inFC2 = r"S:\HQ\Planning\DataResources\Workspace\CTPS\60616_MassDOT_Road_Inventory_Supplemental_Grant\GIS\Data\MassGIS\STREETS_20140616.gdb\STREETS_20140616" # provide a default value if unspecified

inFieldMap = arcpy.GetParameterAsText(2)
if inFieldMap == '#' or not inFieldMap:
    inFieldMap = "" # provide a default value if unspecified
oFieldMappings = arcpy.FieldMappings()
oFieldMappings.loadFromString(inFieldMap)

inKeyField1 = arcpy.GetParameterAsText(3)
if inKeyField1 == '#' or not inKeyField1:
    inKeyField1 = "" # provide a default value if unspecified

inKeyField2 = arcpy.GetParameterAsText(4)
if inKeyField2 == '#' or not inKeyField2:
    inKeyField2 = "" # provide a default value if unspecified

outDiffRecords = arcpy.GetParameterAsText(5)
if outDiffRecords == '#' or not outDiffRecords:
    outDiffRecords = "Differences" # provide a default value if unspecified

inCompareShape = arcpy.GetParameter(6)
if inCompareShape == '#' or not inCompareShape:
    inCompareShape = False

# Utility function to write a difference record
def writeDiffRec(oCursor, iOID1, iOID2, szChangeType, oFeat1=None, oFeat2=None, oFieldMappings=None, bCompareShape=False):
    oNewRow = oCursor.newRow()

    if iOID1:
        oNewRow.setValue("OID_1", iOID1)
    if iOID2:
        oNewRow.setValue("OID_2", iOID2)

    if szChangeType in ["Add", "Delete", "Null key 1", "Null key 2"]:
        oNewRow.setValue("CHANGE_TYPE", szChangeType)
        oCursor.insertRow(oNewRow)
    elif szChangeType == "Edit":
        oNewRow.setValue("CHANGE_TYPE", szChangeType)
        bEdited = False
        if oFeat1 and oFeat2:
            if oFieldMappings:
                for i in range(0, oFieldMappings.fieldCount):
                    oFieldMap = oFieldMappings.getFieldMap(i)
                    if oFeat1.getValue(oFieldMap.getInputFieldName(0)) != oFeat2.getValue(oFieldMap.getInputFieldName(1)):
                        oNewRow.setValue(oFieldMap.outputField.name, 1)
                        bEdited = True
                    else:
                        oNewRow.setValue(oFieldMap.outputField.name, 0)
            if bCompareShape:
                oShape1 = oFeat1.getValue("SHAPE")
                oShape2 = oFeat2.getValue("SHAPE")
                # The .equals() method ignores direction when comparing vectors, so check explicitly that the first point
                # of each shape is within a tolerance distance. The .equals() method cannot be used on the point geometry,
                # since it does not seem to honor the XYTolerance environment setting, so we have to resort to our own
                # Pythagorean calculation. To avoid calculation of square roots, we'll compare the sum of the squares of the
                # rise and run to the square of the desired XYTolerance ( 0.001 ^ 2 = 0.000001 ).
                if oShape1.equals(oShape2):
                    if ((oShape2.firstPoint.X-oShape1.firstPoint.X)**2+(oShape2.firstPoint.Y-oShape1.firstPoint.Y)**2) < 0.000001:
                        oNewRow.setValue("SHAPE", 0)
                    else:
                        oNewRow.setValue("SHAPE", 2)
                        bEdited = True
                else:
                    oNewRow.setValue("SHAPE", 1)
                    bEdited = True
            if bEdited:
                oCursor.insertRow(oNewRow)

        

    
# Make sure that the ArcGIS environment variable workspace is set to something usable before beginning
# In some cases it is blank and should always be set explicitly.
szSavedWorkspace = arcpy.env.workspace
if not arcpy.env.workspace:
    # if it is blank try finding Default.gdb that should be in the user's ArcGIS profile folder
    dll = ctypes.windll.shell32
    buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
    if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
        szUserDefaultGDB = os.path.join(buf.value,u"ArcGIS\\Default.gdb")
        if os.path.exists(szUserDefaultGDB):
            arcpy.env.workspace = szUserDefaultGDB

# Local variables:
arcpy.SetProgressorLabel("Getting count of records...")
iNumRecords = int(arcpy.GetCount_management(inFC1).getOutput(0)) + int(arcpy.GetCount_management(inFC2).getOutput(0))
iNumRecordsCompared = 0
iProgressorIncrement = int(iNumRecords/100)
sFldNameOID1 = arcpy.ListFields(inFC1,"*","OID")[0].baseName
sFldNameOID2 = arcpy.ListFields(inFC2,"*","OID")[0].baseName

# Open sorted feature cursors on two FCs to be compared
arcpy.SetProgressorLabel("Sorting inputs on key field...")
oFeatCursor1 = arcpy.SearchCursor(inFC1, "", "", "", inKeyField1 + " A")
oFeatCursor2 = arcpy.SearchCursor(inFC2, "", "", "", inKeyField2 + " A")

# Open row cursor for output difference table, after creating the table
arcpy.SetProgressorLabel("Preparing output table...")
if arcpy.Exists(outDiffRecords):
    arcpy.Delete_management(outDiffRecords)
arcpy.CreateTable_management(os.path.dirname(outDiffRecords), os.path.basename(outDiffRecords))
arcpy.AddField_management(outDiffRecords, "OID_1", "LONG")
arcpy.AddField_management(outDiffRecords, "OID_2", "LONG")
arcpy.AddField_management(outDiffRecords, "CHANGE_TYPE", "TEXT", "#", "#", "10")
for i in range(0, oFieldMappings.fieldCount):
    arcpy.AddField_management(outDiffRecords, oFieldMappings.getFieldMap(i).outputField.name, "SHORT")
if inCompareShape:
    arcpy.AddField_management(outDiffRecords, "SHAPE", "SHORT")
oRowCursor = arcpy.InsertCursor(outDiffRecords)

# determine data type of key field
sKeyFieldType = arcpy.ListFields(inFC1, inKeyField1)[0].type

# initialize main loop
oFeat1 = oFeatCursor1.next()
oFeat2 = oFeatCursor2.next()
arcpy.SetProgressor("step", "Comparing " + str(iNumRecords) + " combined records in two feature classes...")
arcpy.SetProgressorPosition(0)
iProgressorPosition = 0

# MAIN LOOP
while oFeat1 or oFeat2:
    if not oFeat1:
        writeDiffRec(oRowCursor, "", oFeat2.getValue(sFldNameOID2), "Null key 2" if oFeat2.isNull(inKeyField2) else "Add")
        oFeat2 = oFeatCursor2.next()
        iNumRecordsCompared += 1
    elif oFeat1.isNull(inKeyField1):
        writeDiffRec(oRowCursor, oFeat1.getValue(sFldNameOID1), "", "Null key 1")
        oFeat1 = oFeatCursor1.next()
        iNumRecordsCompared += 1
    elif not oFeat2:
        writeDiffRec(oRowCursor, oFeat1.getValue(sFldNameOID1), "", "Delete")
        oFeat1 = oFeatCursor1.next()
        iNumRecordsCompared += 1
    elif oFeat2.isNull(inKeyField2):
        writeDiffRec(oRowCursor, "", oFeat2.getValue(sFldNameOID2), "Null key 2")
        oFeat2 = oFeatCursor2.next()
        iNumRecordsCompared += 1
    elif oFeat1.getValue(inKeyField1) == oFeat2.getValue(inKeyField2):
        writeDiffRec(oRowCursor, oFeat1.getValue(sFldNameOID1), oFeat2.getValue(sFldNameOID2), "Edit", oFeat1, oFeat2, oFieldMappings, inCompareShape)
        oFeat1 = oFeatCursor1.next()
        oFeat2 = oFeatCursor2.next()
        iNumRecordsCompared += 2
    # NB: The cursor sorts strings respecting locale order rather than strict byte order of characters
    #     (for example "{" sorts before "a" even though its ASCII value is higher).
    #     Therefore a similar comparison is needed in Python if the two cursors are to be traversed in proper order.
    #     The strcoll() function in the Python locale module performs this for us.
    #     We are being lazy by not explicitly setting the locale first, but we hope that Python and
    #     ArcMap both pick up the same locale from the system!
    elif ((oFeat1.getValue(inKeyField1) < oFeat2.getValue(inKeyField2)) if sKeyFieldType != u"String"
          else (locale.strcoll(oFeat1.getValue(inKeyField1), oFeat2.getValue(inKeyField2)) == -1)):
        writeDiffRec(oRowCursor, oFeat1.getValue(sFldNameOID1), "", "Delete")
        oFeat1 = oFeatCursor1.next()
        iNumRecordsCompared += 1
    else:
        writeDiffRec(oRowCursor, "", oFeat2.getValue(sFldNameOID2), "Add")
        oFeat2 = oFeatCursor2.next()
        iNumRecordsCompared += 1

    # update the progressor in the dialog box
    if int(iNumRecordsCompared / iProgressorIncrement) > iProgressorPosition:
        iProgressorPosition += 1
        arcpy.SetProgressorPosition(iProgressorPosition)

# CLEAN UP
arcpy.env.workspace = szSavedWorkspace
