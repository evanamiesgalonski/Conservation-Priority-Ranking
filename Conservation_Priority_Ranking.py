#-------------------------------------------------------------------------------
# Script Name: Land Parcels Conservation Priority Ranking
# Author:      Evan Amies-Galonski
#-------------------------------------------------------------------------------

# The purpose of this script is to calculate and assign a conservation priority ranking for land parcels in Alberta.
# 5 factors are taken into consideration: Lentic (Wetlands), Lotic (Riparian), Intactness, Largest (intact) Patch size, and Proximity to Parks and Protected lands.
# Geoproccessing is used analyze the spatial relationships between the parcels and the data related to each of the 5 factors.
# Parcels recive a score for each factor, then the scores are summed, resulting in a final priority score, and relative ranking for each parcel.

# The output of this script is a feature class containing the desired land parcels. It's attribute table has several additional
# fields, which have been populated with values and scores pertaining to the spatial relationships between the parcels and each of the 5 factors.
# Two more fields contian the values for the parcel's summed Conservation Priority Score and it's Conservation Priority Ranking.


# ##### Notes on the script and its limitations, as a result of the short project timeline #####

# When a very large area of interest is used, there is the possibility that an ArcGIS Topoengine error will occur. Although the definite cause of this has not been verified, it may be a result of
# ArcGIS running out of memory in it's temporary workspace for geoproccessing. For reference, this error occured when testing the script for the entire Stettler county (approx 4350 km^2).

# It is important that the Area of interest polygon is in a projected coordinate system with linear units (meters). An automated method for assessing the current coordinate system and
# projecting it accordingly has not yet been developed.

# Decile statistical classification was used for scoring Lotic, Wetlands, and Quartiles were used to classify the priority ranking. A method for automatedly classifying by natural breaks, or otherwise,
# has not yet been developed.

# A method for including additional, optional conservation factors (eg. mammal habitat) has not yet been developed.

# The ability to adjust distances for proximity scoring has not yet been developed.

# The ability to exclude specific human footprint types has not yet been developed.

# Because of topological errors in the orginal human footprint government data there are tiny gaps in that erroneously connect distinct polygons. This is addressed by buffering the human footprint polygons
# before creating the inverse (intactness). Unfortunatley, this causes the script to crash, which is likely also due to the memory limit in the ArcGIS temporary workspace.
# As a result, the buffer is not included in this version of the script and some of the intact patches are larger than would be considered realistic.




# START SCRIPT #

# first import arcpy
import arcpy

# This section of the script obtains user input for all required perameters of the Priority Ranking function
# The existence and data type of each input is validated

#Parameters are set for valid data types supplied by user
validDataTypes = ["FeatureDataset", "ShapeFile", "FeatureClass"]

# USER INPUT: Workspace
workspace = raw_input("Enter path to the environment workspace for intermediate data and results (Geodatabase):")

while workspace[-3:] != "gdb" or arcpy.Exists(workspace) == False:
    workspace = raw_input("Input is invalid or does not exist, please re-enter file path to workspace (Geodatabase):")
print("workspace OK...")


# USER INPUT: Area of interest polygon
areaOfInterest = raw_input("Enter file path for 'area of interest' polygon:")

while arcpy.Exists(areaOfInterest) == False:
    areaOfInterest = raw_input("Input does not exist. Please re-enter file path to 'area of interest' polygon:")
desc = arcpy.Describe(areaOfInterest)

dataType = desc.dataType
while dataType not in validDataTypes:
    areaOfInterest = raw_input("Input is not the correct data type. Please re-enter file path for the 'area of interest' polygon:")
print("Area of interest OK...")


# USER INPUT: Alberta Riparian(Lotic) polygon data
albertaloticRiparian = raw_input("Enter filepath for the Alberta Riparian/Lotic data")

while arcpy.Exists(albertaloticRiparian) == False:
    albertaloticRiparian = raw_input("Input does not exist. Please re-enter file path for the Alberta Riparian/Lotic data:")
desc = arcpy.Describe(albertaloticRiparian)
dataType = desc.dataType

while dataType not in validDataTypes:
    albertaloticRiparian = raw_input("Input is not the correct data type.  Please re-enter file path for the Alberta Riparian/Lotic data:")
print("Riparian input OK...")


# USER INPUT: Alberta Wetlands data
albertaMergedWetlandInventory = raw_input("Enter filepath for the Alberta Wetlands data")

while arcpy.Exists(albertaMergedWetlandInventory) == False:
    albertaMergedWetlandInventory = raw_input("Input does not exist. Please re-enter file path for the Alberta wetlands data:")
desc = arcpy.Describe(albertaMergedWetlandInventory)

dataType = desc.dataType
while dataType not in validDataTypes:
    albertaMergedWetlandInventory = raw_input("Input is not the correct data type. Please re-enter file path for the Alberta wetlands data:")
print("Wetland input OK...")


# USER INPUT: Alberta Quarter section boundaries data
quarterSectionBoundaries = raw_input("Enter filepath for the Alberta Quarter Section data")

while arcpy.Exists(quarterSectionBoundaries) == False:
    quarterSectionBoundaries = raw_input("Input does not exist. Please re-enter file path for the Alberta Quarter Section data:")
desc = arcpy.Describe(quarterSectionBoundaries)
dataType = desc.dataType

while dataType not in validDataTypes:
    quarterSectionBoundaries = raw_input("Input is not the correct data type.  Please re-enter file path for the Alberta Quarter Section data:")
print("Alberta Quarter Section input OK...")


# USER INPUT: Alberta Parks and Protected Areas data
parksProtectedAreasAlberta = raw_input("Enter filepath for the Alberta Parks and Protected Areas data")

while arcpy.Exists(parksProtectedAreasAlberta) == False:
    parksProtectedAreasAlberta = raw_input("Input does not exist. Please re-enter file path for the Alberta Parks and Protected Areas data:")
desc = arcpy.Describe(parksProtectedAreasAlberta)
dataType = desc.dataType

while dataType not in validDataTypes:
    parksProtectedAreasAlberta = raw_input("Input is not the correct data type.  Please re-enter file path for the Alberta Parks and Protected Areas data:")
print("Parks and Protected Areas input OK...")


# USER INPUT: Alberta Human Footprint data
humanFootprint = raw_input("Enter filepath for the Alberta Human Footprint data")

while arcpy.Exists(humanFootprint) == False:
    humanFootprint = raw_input("Input does not exist. Please re-enter file path for the Alberta Human Footprint data:")
desc = arcpy.Describe(humanFootprint)
dataType = desc.dataType

while dataType not in validDataTypes:
    humanFootprint = raw_input("Input is not the correct data type.  Please re-enter file path for the Alberta Human Footprint data:")
print("Human Footprint input OK...")





# Now our main function is defined. This is the only function, and as long as all the perameters are correctly provided, it should produce the desired result
# (along with intermediate data)
def main(workspace, areaOfInterest, albertaloticRiparian, albertaMergedWetlandInventory, quarterSectionBoundaries, parksProtectedAreasAlberta, humanFootprint):

    # Import necesarry modules
    import numpy as np
    import arcpy

    # Overwrite output and checkout neccesary extensions
    arcpy.env.overwriteOutput = True
    arcpy.CheckOutExtension("spatial")

    # assign workspace
    arcpy.env.workspace = workspace

    # First we project our parcel data into the correct projection, create a layer file, then select only parcels we are interested in with Select by Attribute
    # and Select by Location (Intersecting tht Area of Interest polygon), then export this selection to a new feature class called "ParcelsFinal"

    # Local Variables
    quarterSectionBoundaries_project = "quarterSectionBoundaries_project"
    quarterSectionBoundaries_project_layer = "quarterSectionBoundaries_project_layer"
    ParcelsFinal = "ParcelsFinal"

    # Process: Project
    arcpy.Project_management(quarterSectionBoundaries, quarterSectionBoundaries_project, "PROJCS['NAD_1983_10TM_AEP_Forest',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-115.0],PARAMETER['Scale_Factor',0.9992],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]", "", "GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]", "NO_PRESERVE_SHAPE", "", "NO_VERTICAL")

    # Process: Make Feature Layer
    arcpy.MakeFeatureLayer_management(quarterSectionBoundaries_project, quarterSectionBoundaries_project_layer, "", "", "OBJECTID OBJECTID VISIBLE NONE;Shape Shape VISIBLE NONE;MER MER VISIBLE NONE;RGE RGE VISIBLE NONE;TWP TWP VISIBLE NONE;SEC SEC VISIBLE NONE;QS QS VISIBLE NONE;RA RA VISIBLE NONE;PARCEL_ID PARCEL_ID VISIBLE NONE;Shape_length Shape_length VISIBLE NONE;Shape_area Shape_area VISIBLE NONE")

    # selects all parcels intersecting the users area of interest
    # Process: Select Layer By Location
    arcpy.SelectLayerByLocation_management(quarterSectionBoundaries_project_layer, "INTERSECT", areaOfInterest, "", "NEW_SELECTION", "NOT_INVERT")

    # Removes roads from parcel data to ensure that only quarter sections are selected
    # Process: Select Layer By Attribute
    arcpy.SelectLayerByAttribute_management(quarterSectionBoundaries_project_layer, "SUBSET_SELECTION", "RA NOT LIKE 'R'")

    # Process: Copy Features
    arcpy.CopyFeatures_management(quarterSectionBoundaries_project_layer, ParcelsFinal, "", "0", "0", "0")


    # ############### ArcGis MODEL BUILDER SECTION: for initial Geoproccessing #################################################################################################################


    # The following was exported from ArcMap's Model builder. It performs most of the neccessary geoprocessing needed to determine the spatial relationships
    # between the parcels and the user provided data (Human footprint, Lotic(Riparian), Wetlands, Patch Size, and Proximity)

    # local Variables:
    footprint_EXTENT_CLIPPED = "Footprint_Extent_Clipped"
    Footprint_Inverse = "Footprint_Inverse"
    Intact_Area_Per_Parcel = "Intact_Area_Per_Parcel"
    Wetland_Extent_Clipped = "Wetland_Extent_Clipped"
    Wetland_Lines = "Wetland_Lines"
    Wetland_Edge_Per_Parcel = "Wetland_Edge_Per_Parcel"
    Lotic_Extent_Clipped = "Lotic_Extent_Clipped"
    Lotic_No_Wetlands = "Lotic_No_Wetlands"
    Lotic_Area_Per_Parcel = "Lotic_Area_Per_Parcel"
    Area_Of_Interest_Buffered = "Area_Of_Interest_Buffered"
    Footprint_Larger_Extent = "Footprint_Larger_Extent"
    Footprint_INVERSE_Large = "Footprint_INVERSE_Large"
    Footprint_INVERSE_Large_Explode = "Footprint_INVERSE_Large_Explode"

    # Process: Clip
    arcpy.Clip_analysis(humanFootprint, ParcelsFinal, footprint_EXTENT_CLIPPED, "")

    # Process: Erase
    arcpy.Erase_analysis(ParcelsFinal, footprint_EXTENT_CLIPPED, Footprint_Inverse, "")

    #
    # Process: Tabulate Intersection
    arcpy.TabulateIntersection_analysis(ParcelsFinal, "OBJECTID", Footprint_Inverse, Intact_Area_Per_Parcel, "", "", "", "UNKNOWN")

    # Process: Clip (3)
    arcpy.Clip_analysis(albertaMergedWetlandInventory, ParcelsFinal, Wetland_Extent_Clipped, "")

    # Process: Feature To Line
    arcpy.FeatureToLine_management(Wetland_Extent_Clipped, Wetland_Lines, "", "ATTRIBUTES")
    ##arcpy.FeatureToLine_management("'D:\\evanamiesgalonskiMOBILE\\1 Courses\\329\\Final Project\\DATA\\test results.gdb\\Wetland_Extent_Clipped'", Wetland_Lines, "", "ATTRIBUTES")

    # Process: Tabulate Intersection (2)
    arcpy.TabulateIntersection_analysis(ParcelsFinal, "OBJECTID", Wetland_Lines, Wetland_Edge_Per_Parcel, "", "", "", "UNKNOWN")

    # Process: Clip (4)
    arcpy.Clip_analysis(albertaloticRiparian, ParcelsFinal, Lotic_Extent_Clipped, "")

    # Process: Erase (2)
    arcpy.Erase_analysis(Lotic_Extent_Clipped, Wetland_Extent_Clipped, Lotic_No_Wetlands, "")

    # Process: Tabulate Intersection (3)
    arcpy.TabulateIntersection_analysis(ParcelsFinal, "OBJECTID", Lotic_No_Wetlands, Lotic_Area_Per_Parcel, "", "", "", "UNKNOWN")

    # Process: Buffer
    arcpy.Buffer_analysis(areaOfInterest, Area_Of_Interest_Buffered, "50 Kilometers", "FULL", "ROUND", "NONE", "", "PLANAR")

    # Process: Clip (2)
    arcpy.Clip_analysis(humanFootprint, Area_Of_Interest_Buffered, Footprint_Larger_Extent, "")

    # Process: Erase (3)
    arcpy.Erase_analysis(Area_Of_Interest_Buffered, Footprint_Larger_Extent, Footprint_INVERSE_Large, "")

    # Process: Multipart To Singlepart
    arcpy.MultipartToSinglepart_management(Footprint_INVERSE_Large, Footprint_INVERSE_Large_Explode)

    # ###########################################################################################################################################################################


    # This part of the script edits the nwely created tables that contain information about the instersection of Wetlands, Lotic, and Intactness data with the land parcels
    # The Area and Percent coverage fields are renamed to be more decriptive and to ensure there are no confusing duplicate field names in our ParcelsFinal feature class.

    # Alter Field names in intactness table
    arcpy.AlterField_management(Intact_Area_Per_Parcel, "AREA", new_field_name = "Area_Intact", field_is_nullable = "NULLABLE")
    arcpy.AlterField_management(Intact_Area_Per_Parcel, "PERCENTAGE", new_field_name = "Percent_Intact", field_is_nullable = "NULLABLE")

    # Alter field names in lotic_table
    arcpy.AlterField_management(Lotic_Area_Per_Parcel, "AREA", new_field_name = "Area_Lotic", field_is_nullable = "NULLABLE")
    arcpy.AlterField_management(Lotic_Area_Per_Parcel, "PERCENTAGE", new_field_name = "Percent_Lotic", field_is_nullable = "NULLABLE")

    # Alter Field name in wetlands_table
    arcpy.AlterField_management(Wetland_Edge_Per_Parcel, "LENGTH", new_field_name = "Wetland_Edge", field_is_nullable = "NULLABLE")


    # Now we will join the desired fields from the 3 tables (intactness, lotic, ad wetlands) to the Land Parcel feature class

    # Process: Join Field
    arcpy.JoinField_management(ParcelsFinal, "OBJECTID", Intact_Area_Per_Parcel, "OBJECTID_1", ["Area_Intact", "Percent_Intact"])

    # Process: Join Field (2)
    arcpy.JoinField_management(ParcelsFinal, "OBJECTID", Lotic_Area_Per_Parcel, "OBJECTID_1", ["Area_Lotic", "Percent_Lotic"])

    # Process: Join Field (3)
    arcpy.JoinField_management(ParcelsFinal, "OBJECTID", Wetland_Edge_Per_Parcel, "OBJECTID_1", "Wetland_Edge")


    # Now we get rid of null values in our new fields and replace them with zeros

    with arcpy.da.UpdateCursor(ParcelsFinal, ["Area_Intact"]) as cursor:
        for row in cursor:
            if row[0] == None:
                row[0] = 0
                cursor.updateRow(row)

    with arcpy.da.UpdateCursor(ParcelsFinal, ["Percent_Intact"]) as cursor:
        for row in cursor:
            if row[0] == None:
                row[0] = 0
                cursor.updateRow(row)

    with arcpy.da.UpdateCursor(ParcelsFinal, ["Area_Lotic"]) as cursor:
        for row in cursor:
            if row[0] == None:
                row[0] = 0
                cursor.updateRow(row)

    with arcpy.da.UpdateCursor(ParcelsFinal, ["Percent_Lotic"]) as cursor:
        for row in cursor:
            if row[0] == None:
                row[0] = 0
                cursor.updateRow(row)

    with arcpy.da.UpdateCursor(ParcelsFinal, ["Wetland_Edge"]) as cursor:
        for row in cursor:
            if row[0] == None:
                row[0] = 0
                cursor.updateRow(row)


    # This section of the script calculates the largest intact patch that intersects each parcel

    # Local Variables
    Footprint_INVERSE_Large_Explode = "Footprint_INVERSE_Large_Explode"
    Patch_Sizes_Per_Parcel = "Patch_Sizes_Per_Parcel"

    # Process: Tabulate Intersection
    arcpy.TabulateIntersection_analysis(ParcelsFinal, "OBJECTID", Footprint_INVERSE_Large_Explode, Patch_Sizes_Per_Parcel, "SHAPE_Area", "", "", "UNKNOWN")

    # A table was created with Tabulate Intersection that contains the areas of all intact patches that intersect
    # each parcel. We have several duplicates of each Parcel OBJECTID in this table, one for every patch that intersects a parcel.
    # we need to determine which duplicate OBJECTID corresponds to the largest patch area.

    # First we get a full list of the object IDs in our clipped ParcelsFinal Class
    # even though there is only one value in each cell of the attribute table, the data type is a tuple, so we need to extract our value our of it, as with a list
    parcel_IDs_extracted = []
    parcel_IDs = arcpy.da.SearchCursor(ParcelsFinal, "OBJECTID")
    for ID in parcel_IDs:
        if isinstance(ID, tuple):
            ID = ID[0]
            parcel_IDs_extracted.append(ID)
        else:
            parcel_IDs_extracted.append(ID)


    Patch_Sizes_Per_Parcel = "Patch_Sizes_Per_Parcel"

##    # remove null values
##    with arcpy.da.UpdateCursor(Patch_Sizes_Per_Parcel, ["SHAPE_Area"]) as cursor:
##        for row in cursor:
##            if row[0] == None:
##                row[0] = 0
##                cursor.updateRow(row)


    # Now we get a full list of all of the Parcel Object ID that had at least one intersection with the "Intact" feature class (human footprint inverse)
    # NOTE: not all of the parcels in our area of interest necessarily intersect with the "Intact" feature class
    patch_IDs = arcpy.da.SearchCursor(Patch_Sizes_Per_Parcel, "OBJECTID_1")
    patch_IDs_extracted = []
    for ID in patch_IDs:
        if isinstance(ID, tuple):
            ID = ID[0]
            patch_IDs_extracted.append(ID)
        elif isinstance(ID, str):
            patch_IDs_extracted.append(ID)



    # initialize 2 new lists
    orderedListofLists = []
    newlist = []
    # for each OBJECT ID we create a list of areas which are the intsects for a parcel, then append that list as an element in our list of lists (orderedListofLists)
    # the newlist is re-initialized every intereation after it has dumped its values into the orderedlistoflists. The orderedlistoflists is not re-initialized, and continues to be appended to.
    # Now the intersections for each parcel are nicely grouped together
    for ID in parcel_IDs_extracted:
        patch_IDs_and_Areas = arcpy.da.SearchCursor(Patch_Sizes_Per_Parcel, ["OBJECTID_1", "SHAPE_Area"])
        if ID not in patch_IDs_extracted: # This step ensures that parcels that have not intersection receive a zero instead of being glossed over. This will maintain order of our field values.
            orderedListofLists.append(0)
        else:
            newlist = []
            for rows in patch_IDs_and_Areas:
                if ID == rows[0]:
                    x = rows[1]
                    newlist.append(x)
            orderedListofLists.append(newlist)

    # initialize one more list
    # Since the intersections(areas) are grouped by parcel, we extract the highest number in each list element (which is a list), and this give us the largest patch size for each parcel.
    max_patch_size_per_parcel = []

    for patchSizes in orderedListofLists:
        if patchSizes == 0:
            max_patch_size_per_parcel.append(0)
        else:
            max_patch_size_per_parcel.append(max(patchSizes))

    # convert to acres for scoring
    max_patch_size_per_parcel_acres = []
    acre = 0
    for patchsize in max_patch_size_per_parcel:
        acre = patchsize / 4046.86
        max_patch_size_per_parcel_acres.append(acre)


    # Now we have a list that contains the largest patch that intersects each parcel.
    # It is ordered the same as the OBJECTID and we can now create a new field in the parcels feature class and
    # iteratively polulate the rows with each patch area value

    # create new field
    arcpy.AddField_management(ParcelsFinal, "Largest_Patch_Area", "DOUBLE", field_length = 50)

    # initialize x
    x = 0

    # use update cursor to populate rows and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "Largest_Patch_Area") as cursor:
        for row in cursor:
            row[0] = max_patch_size_per_parcel_acres[x]
            cursor.updateRow(row)
            x += 1


    # the following code calculates the nearest protected area feature and automatically creates a new field that contains that distance for each parcel.
    # Process: Near
    arcpy.Near_analysis(ParcelsFinal, parksProtectedAreasAlberta, "", "NO_LOCATION", "NO_ANGLE", "PLANAR")


    # #######################################################################################################################################################################################################

    # The next section of code calulates the scores for each parcel based on the values is our newly added/created fields.


    # ##################### INTACTNESS SCORE #######################

    # extract percent intact field
    intact_scores = []
    percent_intact = arcpy.da.SearchCursor(ParcelsFinal, "Percent_Intact")
    # Perform calulation for score and append to new list. Accomodate for str and tuple field types
    for percent in percent_intact:
        if isinstance(percent, tuple):
            percent = percent[0] / 100
        elif isinstance(percent, str):
            percent = float(percent)
        intact_scores.append(percent)

    # create new field
    arcpy.AddField_management(ParcelsFinal, "SCORE_Intactness", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "SCORE_Intactness") as cursor:
        for row in cursor:
            row[0] = intact_scores[x]
            cursor.updateRow(row)
            x += 1


    # ################### Lotic (Riparian) Score #########################

    # extract percent lotic field
    lotic_percent_list = []
    percent_lotic = arcpy.da.SearchCursor(ParcelsFinal, "Percent_Lotic")
    #  Accomodate for str and tuple field types
    for percent in percent_lotic:
        if isinstance(percent, tuple):
            percent = percent[0]
        elif isinstance(percent, str):
            percent = float(percent)
        lotic_percent_list.append(percent)


    # now we create a create a lotic percent list no zeros before establishing ranges for deciles
    lotic_percent_list_noZero = []
    for percent in lotic_percent_list:
        if percent != 0:
            lotic_percent_list_noZero.append(percent)

    # use numbpy to calculate the decile ranges
    ranges = np.percentile(lotic_percent_list_noZero, np.arange(0, 100, 10))


    # iterate through origincal lotic percent list and use the decile ranges to bin the lotic percent values to the appropriate scores
    final_lotic_scores = []
    for percent in lotic_percent_list:
        if percent == 0:
            final_lotic_scores.append(0)
        elif percent >= ranges[0] and percent <= ranges[1]:
             final_lotic_scores.append(0.1)
        elif percent >= ranges[1] and percent <= ranges[2]:
            final_lotic_scores.append(0.2)
        elif percent >= ranges[2] and percent <= ranges[3]:
            final_lotic_scores.append(0.3)
        elif percent >= ranges[3] and percent <= ranges[4]:
            final_lotic_scores.append(0.4)
        elif percent >= ranges[4] and percent <= ranges[5]:
            final_lotic_scores.append(0.5)
        elif percent >= ranges[5] and percent <= ranges[6]:
            final_lotic_scores.append(0.6)
        elif percent >= ranges[6] and percent <= ranges[7]:
            final_lotic_scores.append(0.7)
        elif percent >= ranges[7] and percent <= ranges[8]:
            final_lotic_scores.append(0.8)
        elif percent >= ranges[8] and percent <= ranges[9]:
            final_lotic_scores.append(0.9)
        elif percent >= ranges[9]:
            final_lotic_scores.append(1)


    # the order of the resulting list is identical to the original, so it can be appended as a new field and the values will
    # correspond with the rows they are meant to score

    # create new field
    arcpy.AddField_management(ParcelsFinal, "SCORE_Lotic_Deciles", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "SCORE_Lotic_Deciles") as cursor:
        for row in cursor:
            row[0] = final_lotic_scores[x]
            cursor.updateRow(row)
            x += 1


    # ######################### Wetland Score #####################

    # extract Wetland edge length field
    wetland_edge_list = []
    wetland_field = arcpy.da.SearchCursor(ParcelsFinal, "Wetland_Edge")

    # append values to new list. Accomodate for str and tuple field types.
    for length in wetland_field:
        if isinstance(length, tuple):
            length = length[0]
        elif isinstance(length, str):
            length = float(length)
        wetland_edge_list.append(length)


    # now we create a create a wetland edge list no zeros before establishing ranges for deciles
    wetland_edge_list_noZero = []
    for edge_length in wetland_edge_list:
        if edge_length != 0:
            wetland_edge_list_noZero.append(edge_length)


    # use numbpy to calculate the decile ranges
    ranges = np.percentile(wetland_edge_list_noZero, np.arange(0, 100, 10))


    # iterate through original wetland edge list and use the decile ranges to bin the wetland edge values to the appropriate scores
    final_wetland_scores = []
    for edge_length in wetland_edge_list:
        if edge_length == 0:
            final_wetland_scores.append(0)
        elif edge_length >= ranges[0] and edge_length <= ranges[1]:
             final_wetland_scores.append(0.1)
        elif edge_length >= ranges[1] and edge_length <= ranges[2]:
            final_wetland_scores.append(0.2)
        elif edge_length >= ranges[2] and edge_length <= ranges[3]:
            final_wetland_scores.append(0.3)
        elif edge_length >= ranges[3] and edge_length <= ranges[4]:
            final_wetland_scores.append(0.4)
        elif edge_length >= ranges[4] and edge_length <= ranges[5]:
            final_wetland_scores.append(0.5)
        elif edge_length >= ranges[5] and edge_length <= ranges[6]:
            final_wetland_scores.append(0.6)
        elif edge_length >= ranges[6] and edge_length <= ranges[7]:
            final_wetland_scores.append(0.7)
        elif edge_length >= ranges[7] and edge_length <= ranges[8]:
            final_wetland_scores.append(0.8)
        elif edge_length >= ranges[8] and edge_length <= ranges[9]:
            final_wetland_scores.append(0.9)
        elif edge_length >= ranges[9]:
            final_wetland_scores.append(1)


    # the order of the resulting list is identical to the original, so it can be appended as a new field and the values will
    # correspond with the rows they are meant to score

    # create new field
    arcpy.AddField_management(ParcelsFinal, "SCORE_Wetland_Deciles", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "SCORE_Wetland_Deciles") as cursor:
        for row in cursor:
            row[0] = final_wetland_scores[x]
            cursor.updateRow(row)
            x += 1



    # ################ Patch size score ####################

    # extract patch size field
    largest_patch_sizes = []
    patch_sizes = arcpy.da.SearchCursor(ParcelsFinal, "Largest_Patch_Area")
    # Perform calulation for score and append to new list. Accomodate for str and tuple field types
    for size in patch_sizes:
        if isinstance(size, tuple):
            size = size[0]
        elif isinstance(size, str):
            size = float(size)
        largest_patch_sizes.append(size)

    # now we populate a new list and assign scores based on number ranges
    patch_size_scores = []
    for size in largest_patch_sizes:
        if size < 160:
            patch_size_scores.append(0)
        elif size > 160 and size < 2500:
             patch_size_scores.append(0.5)
        elif size > 2500 and size < 10000:
            patch_size_scores.append(.75)
        elif size > 10000:
            patch_size_scores.append(1)


    # create new field
    arcpy.AddField_management(ParcelsFinal, "SCORE_Patch_Size", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "SCORE_Patch_Size") as cursor:
        for row in cursor:
            row[0] = patch_size_scores[x]
            cursor.updateRow(row)
            x += 1


    # ############### Proximity Score #####################

    # Rename Distance field to be more decriptive
    # delete NEAD FID feild (un-needed)
    arcpy.AlterField_management(ParcelsFinal, "NEAR_DIST", new_field_name = "Dist_to_Protected", field_is_nullable = "NULLABLE")
    arcpy.DeleteField_management(ParcelsFinal, "NEAR_FID")

    # extract proximity field
    all_proximities = []
    proximities = arcpy.da.SearchCursor(ParcelsFinal, "Dist_to_Protected")
    # Perform calulation for score and append to new list. Accomodate for str and tuple field types
    for proximity in proximities:
        if isinstance(proximity, tuple):
            proximity = proximity[0]
        elif isinstance(proximity, str):
            proximity = float(proximity)
        all_proximities.append(proximity)

    # now we populate a new list and assign scores based on number ranges
    proximity_scores = []
    for proximity in all_proximities:
        if proximity == 0:
            proximity_scores.append(1)
        elif proximity > 0 and proximity < 2000:
             proximity_scores.append(0.75)
        elif proximity > 2000 and proximity < 4000:
            proximity_scores.append(.5)
        elif proximity > 4000:
            proximity_scores.append(0)


    # create new field
    arcpy.AddField_management(ParcelsFinal, "SCORE_Proximity", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "SCORE_Proximity") as cursor:
        for row in cursor:
            row[0] = proximity_scores[x]
            cursor.updateRow(row)
            x += 1


    # ##################### FINAL PRIORITY SCORES ###########################

    sumOfScores = []
    scoreFields = arcpy.da.SearchCursor(ParcelsFinal,["SCORE_Lotic_Deciles", "SCORE_Wetland_Deciles", "SCORE_Intactness", "SCORE_Patch_Size", "SCORE_Proximity"])
    for score in scoreFields:
        sumScore = score[0] + score[1] + score[2] + score[3] +score[4]
        sumOfScores.append(sumScore)


    # create new field
    arcpy.AddField_management(ParcelsFinal, "PRIORITY_SCORE", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "PRIORITY_SCORE") as cursor:
        for row in cursor:
            row[0] = sumOfScores[x]
            cursor.updateRow(row)
            x += 1
    # the order of the resulting list is identical to the original, so it can be appended as a new field and the values will
    # correspond with the rows they are meant to score


    # ################################## PRIORITY RANKING #######################################

    # now we calculate ranges for priority ranking with 4 breaks (Quartiles)
    ranges = np.percentile(sumOfScores, np.arange(0, 100, 25))

    final_priority_ranking = []
    for score in sumOfScores:
        if score >= ranges[0] and score <= ranges[1]:
             final_priority_ranking.append(None)
        elif score >= ranges[1] and score <= ranges[2]:
            final_priority_ranking.append(3)
        elif score >= ranges[2] and score <= ranges[3]:
            final_priority_ranking.append(2)
        elif score >= ranges[3]:
            final_priority_ranking.append(1)


    # create new field
    arcpy.AddField_management(ParcelsFinal, "PRIORITY_RANKING", "DOUBLE", field_length = 50)

    x = 0

    # use update cursor to populate rows with list element and after each time the cursor moves down to the next row,
    # iterate to the next list element (x)
    with arcpy.da.UpdateCursor(ParcelsFinal, "PRIORITY_RANKING") as cursor:
        for row in cursor:
            row[0] = final_priority_ranking[x]
            cursor.updateRow(row)
            x += 1

    arcpy.CheckInExtension("spatial")

    print("proccess complete")
    print("...........")
    print("The resulting priority scored parcels feature class can be found in the user specified geodatabase by the name of 'ParcelsFinal'")
    print("To view the Conservation Priority ranking, symbolize the feature class by unique values, using the 'PRIORITY_RANKING' field.")

main(workspace, areaOfInterest, albertaloticRiparian, albertaMergedWetlandInventory, quarterSectionBoundaries, parksProtectedAreasAlberta, humanFootprint)













