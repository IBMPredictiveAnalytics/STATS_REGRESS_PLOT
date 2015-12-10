#Licensed Materials - Property of IBM
#IBM SPSS Products: Statistics General
#(c) Copyright IBM Corp. 2014
#US Government Users Restricted Rights - Use, duplication or disclosure 
#restricted by GSA ADP Schedule Contract with IBM Corp.

__author__ = "IBM SPSS, JKP"
__version__ = "1.0.1"

# history
# 07-15-2011  original version

# Requires at least Statistics version 18

import spss, spssaux
from extension import Template, Syntax, processcmd


helptext="""
Produce plots helpful in assessing regression types of relationships.
These are scatterplots or categorical plots of pairs of variables.  They
are not partial plots.

STATS REGRESS PLOT YVARS=variable list XVARS = variable list
[COLOR=var] [SIZE=var] [SHAPE=var] [LABEL=var]
[/OPTIONS [CATEGORICAL={BAR*|LINE|BOXPLOT}] [GROUP=n]
[BOXPLOTS] [HEXBIN] [TITLE="text"] [INDENT=pct] [YSCALE=pct] [PAGEX=number PAGEY=number]]
[/FITLINES [LINEAR] [QUADRATIC] [CUBIC] [LOESS] [APPLYTO={TOTAL*|GROUP}]
[/HELP]

Example:
STATS REGRESS PLOT YVARS = y1 y2 XVARS=x1 x2 x3 c1
COLOR=z LABEL=id
/OPTIONS GROUP=3
/FITLINES LINEAR APPLYTO=GROUP.

x1, x2, and x3 are scale variables and c1 and c2 are categorical.
This command produces six scatterplots - each y with each x and two bar charts of means.
Points in the scatterplots are colored according the the values of z and labeled by id.
There are three plots per line, and the scatterplots have linear fits for each group as defined
by z.

YVARS lists the variables to be used on the vertical axis, and XVARS lists the variables
for the horizontal axis.  Y-variables must have a scale measurement level.  The level of the
X variables determines the type of plot.
COLOR, SIZE, SHAPE, and LABEL apply to points in the scatterplots and  boxplots except
as noted under GROUP..
The SHAPE variable must be categorical.

CATEGORICAL can be BAR, LINE, or BOXPLOT to indicate the type of plot when
a categorical x variable is used.
GROUP specifies the number of plots to panel on one line, defaulting to 1.  If more than
one is specified, the legend does not appear, but legend information is reported in a
separate table.

HEXBIN causes points to be grouped into bins.  This can be particularly useful
when there are many points or when you want to focus on isolated points.

If GROUP is 1 then for scale variables, bordering boxplots will be produced if
BOXPLOTS is specified.  In that case, the legends are not shown with the charts.
The scales of the bordered plots will approximately match the scatter scales.

TITLE can specify a chart title when group is 1 and boxplot borders are not
requested.

By default, layout is automatic with group > 1, but if the labels are long, text
can be clipped.  INDENT and YSCALE can be used to adjust the layout.  Values
are in percent.

Default size for charts, including a grouped set, can be overridden by specifying
PAGEX and PAGEY (specify both or neither) in points.

FITLINES for scatterplots can be specified.  Available fits are LINEAR, QUADRATIC,
or CUBIC polynomials or a LOESS smooth.  Zero or more can be specified.

By default, fitlines are for the all the points (APPLYTO=TOTAL).  APPLYTO=GROUP
produces a separate fit line for each group if the group is defined by a COLOR
variable, and the color variable is categorical.

/HELP displays this help and does nothing else.
"""


# parameters: allvars, options
ggraphtemplate = r"""GGRAPH /GRAPHDATASET NAME="graphdataset"
VARIABLES= %(allvars)s
/GRAPHSPEC SOURCE=INLINE.
BEGIN GPL
SOURCE: s=userSource(id("graphdataset") %(options)s)
"""
# parameters: varname, unitcategory
datatemplate = """DATA: %(varname)s = col(source(s), name("%(varname)s") %(unitcategory)s)
"""
#parameters: dim, varlabel, other
guidetemplate = """GUIDE: axis(dim(%(dim)s), label("%(varlabel)s") %(other)s)
"""
endgpl = "END GPL."

#parameters: title
titletemplate = """GUIDE: text.title(label("%(title)s"))
"""
# parameters: originandscale
graphstarttemplate = """GRAPH: begin(%(originandscale)s)
"""
graphendtemplate = """GRAPH: end()
"""
# parameters" pagex, pagey
pagestarttemplate = """PAGE: begin(scale(%(pagex)sin, %(pagey)sin))
"""
pageendtemplate = """PAGE: end()
"""
iscat = ", unit.category()"

include0 = """SCALE: linear(dim(2), include(0))
"""
noyaxis = """GUIDE: axis(dim(2), null())
"""
# parameters: x, y, options
scatterelement = """ELEMENT: point(position(%(x)s * %(y)s) %(options)s)
"""
# parameters: x, y, options
hexbinscatterelement = """ELEMENT: point(position(bin.hex(%(x)s * %(y)s)) %(options)s)
"""
# parameters: fittype, x, y, lineshape, color
fitlineelement = """ELEMENT: line(position(smooth.%(fittype)s(%(x)s * %(y)s)), shape(shape.%(lineshape)s) %(color)s)
"""

# aesthetic suppressor
# parameter: aesthetic type
aesth = """GUIDE: legend(aesthetic(aesthetic.%(atype)s), null())"""

# parameters: etype, x, y
categoricalelement = """ELEMENT: %(etype)s(position(summary.mean(%(x)s * %(y)s)))
"""

elementmap = {"bars":"interval", "lines": "line"}

# parameters: x, y, options
boxplotelement = """ELEMENT: schema(position(bin.quantile.letter(%(x)s * %(y)s)) %(options)s)
"""

# parameters: variable
oneboxplotelement = """ELEMENT: schema(position(bin.quantile.letter(%(variable)s)), size(size."80%%"))
"""

fittypekwd = ['linear','quadratic','cubic','loess']   # fit line types
fittypetable = ["LINEAR(solid)", "QUADRATIC(dash)", "CUBIC(longdash)", "LOESS(dashdot)"]
lineshapes = ["solid", "dash","dash_3x", "dash_1_dot"]

def plots(yvars, xvars, color=None, size=None, shape=None, label=None,
    linear=False, quadratic=False, cubic=False, loess=False, ignore=False, title="",
    categorical="bars", group=1, boxplots=False, hexbin=False, applyfitto="total", 
    indent=15, yscale=75, pagex=None, pagey=None):
    """Create plots per specifcation described in help above"""
    
        # debugging
    # makes debug apply only to the current thread
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(2)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ##    ###SpssClient._heartBeat(False)
    #except:
        #pass
    
    npage = [pagex, pagey].count(None)  # 0 means both specified
    if npage == 1:
        raise ValueError(_("Page specification must include both x and y sizes"))
    if group > 1:
        boxplots = False
    spssweight = spss.GetWeightVar()
    if not spssweight:
        spssweight = None

    
    vardict = spssaux.VariableDict()
    # display pivot table of legend information
    fits = []
    for i, fittype in enumerate([linear, quadratic, cubic, loess]):
        if fittype:
            fits.append(fittypetable[i])

    spss.StartProcedure("STATS REGRESS", _("Relationship Plots"))
    ttitle = _("Chart Legend Information")
    if title:
        ttitle = ttitle + "\n" + title
    tbl = spss.BasePivotTable(ttitle, "CHARTLEGENDINFO", caption=_("Legend Settings for the charts that follow.  Some settings do not apply to categorical charts."))
    tbl.SimplePivotTable(_("Settings"),
        rowlabels=[_("Color by"), _("Size by"), _("Shape by"), _("Label by"), _("Fit Lines")],
        collabels=[_("Value")],
        cells = [labelit(color, vardict) or "---", 
            labelit(size, vardict) or "---", 
            labelit(shape, vardict) or "---", 
            labelit(label, vardict) or "---", 
            "\n".join(fits) or "---"])
    spss.EndProcedure()

    # group fitlines only available for categorically defined groups
    if not color or (color and vardict[color].VariableLevel == "scale"):
        applyfitto = "total"

    aesthetics = set([item for item in [color, size, shape, label, spssweight] if not item is None])
    
    for y in yvars:
        yobj = vardict[y]
        if yobj.VariableLevel != "scale":
            raise ValueError(_("Y variables must have a scale measurement level: %s") % y)
        yvarlabel = yobj.VariableLabel or y

        # construct one possibly multi-part chart for each numcharts variables
        for xpart in xgen(xvars, group):
            first = True
            cmd = []
            numcharts = len(xpart)
            mostvariables = " ".join(set(xpart + list(aesthetics)))  # eliminate duplicates (except with y)
            if spssweight:
                options = ", weight(%s)" % spssweight
            else:
                options = ""
            cmd.append(ggraphtemplate % {"allvars" : y + " " + mostvariables, "options" : options})
            indentx = indent
            if npage == 0:    # page specs were given
                if numcharts < group:  # short row
                    shortpagex = pagex * indent / 100. + pagex * (100. - indent)/100. * (float(numcharts) / group)
                    indentx = indent * (pagex/shortpagex)
                    cmd.append(pagestarttemplate % {"pagex": shortpagex, "pagey": pagey})
                else:
                    cmd.append(pagestarttemplate % {"pagex": pagex, "pagey": pagey})
            cmd.append(datatemplate % {"varname" : y, "unitcategory": ""})
            alldatastatements = set([y.lower()])
            if spssweight:
                cmd.append(gendata(spssweight, vardict, alldatastatements))

            # loop over one or more x variables for this chart
            for currentn, x in enumerate(xpart):
                xobj = vardict[x]
                ml = xobj.VariableLevel
                if numcharts > 1:
                    cmd.append(graphstarttemplate % {"originandscale" : scaling(numcharts, currentn, indentx, yscale)})
                if boxplots and ml == "scale":
                    cmd.append(graphstarttemplate % {"originandscale" : "origin(15%, 10%), scale(75%,75%)"})
                if ml == "scale":   # build scatterplot specs
                    uc = ""
                    options = ""
                    if size:
                        options = options + ", size(%s)" % size
                        cmd.append(gendata(size, vardict, alldatastatements))
                        if numcharts > 1:
                            cmd.append(aesth % {"atype": "size"})
                    if color:
                        options = options + ", color.exterior(%s)" % color
                        cmd.append(gendata(color, vardict, alldatastatements))
                        if numcharts > 1:
                            cmd.append(aesth % {"atype" : "color.exterior"})
                    if shape:
                        if vardict[shape].VariableLevel == "scale":
                            raise ValueError(_("The shape variable must be categorical: %s") % shape)
                        options = options + ", shape(%s)" % shape
                        cmd.append(gendata(shape, vardict, alldatastatements))
                        if numcharts > 1:
                            cmd.append(aesth % {"atype" : "shape"})
                else:
                    uc = iscat
                    if categorical == "bars":
                        cmd.append(include0)
                if not first:
                    other = ", null()"
                else:
                    other = ""
                if title and numcharts == 1 and not boxplots:
                    cmd.append(titletemplate % {"title": title})
                cmd.append(gendata(x, vardict, alldatastatements))
                if label:
                    cmd.append(gendata(label, vardict, alldatastatements))
                #cmd.append(datatemplate % {"varname": x, "unitcategory": uc})
                cmd.append(guidetemplate % {"dim":1, "varlabel": xobj.VariableLabel or x, "other": ""})
                if first:
                    cmd.append(guidetemplate % {"dim":2, "varlabel":yvarlabel, "other": other})
                else:
                    cmd.append(noyaxis)
                if ml == "scale":
                    if label:
                        options = options + ", label(%s))" % label
                    if hexbin:
                        cmd.append(hexbinscatterelement % {"y": y, "x": x, "options": options})
                    else:
                        cmd.append(scatterelement % {"y": y, "x": x, "options": options})
                    for i, fittype in enumerate([linear, quadratic, cubic, loess]):
                        if fittype:
                            if applyfitto == "group":
                                colorspec = ", color(%s)" % color
                            else:
                                colorspec = ""
                            if numcharts > 1:
                                cmd.append(aesth % {"atype" : "color"})
                            cmd.append(fitlineelement % \
                                {"fittype": fittypekwd[i], "y": y, "x": x, "lineshape" : lineshapes[i], "color" : colorspec})
                    if boxplots:  # bordered boxplot if single variable chart
                        cmd.append(graphendtemplate)
                        cmd.append(graphstarttemplate % {"originandscale" : "origin(15%, 0%), scale(75%,8%)"})
                        cmd.append("""GUIDE: axis(dim(1), ticks(null()))""")
                        cmd.append("""COORD: rect(dim(1))""")
                        cmd.append(oneboxplotelement % {"variable" : x})
                        cmd.append(graphendtemplate)
                        cmd.append(graphstarttemplate % {"originandscale" : "origin(92%, 10%), scale(8%, 75%)"})
                        cmd.append("COORD: transpose(rect(dim(1)))")
                        cmd.append("""GUIDE: axis(dim(1), ticks(null()))""")
                        cmd.append(oneboxplotelement % {"variable" : y})
                        cmd.append(graphendtemplate)

                else:
                    if categorical != "boxplot":
                        cmd.append(categoricalelement % {"etype" : elementmap[categorical], "y": y, "x": x})
                    else:
                        if label:
                            options = ", label(%s)" % label
                        else:
                            options = ""
                        cmd.append(boxplotelement % {"y":y, "x":x, "options": options})
                first = False
                if numcharts > 1:
                    cmd.append(graphendtemplate)
            if npage == 0:
                cmd.append(pageendtemplate)
            cmd.append(endgpl)
            spss.Submit(cmd)

def xgen(lis, n):
    """Return groups of n items from lis
    
    lis is the list of items to process
    n is the number of items to return each time"""
    
    for i in range(0, len(lis), n):
        yield lis[i:i+n]
        
def gendata(varname, vardict, alldatastatements):
    """Generate a DATA statement possibly with categorical declaration
    
    varname is the variable name to be accessed.  If blank or None, do nothing
    vardict is a VariableDict object
    alldatastatements is a set for tracking to avoid duplicate data statements"""
    
    if not varname:
        return ""
    varnamelc = varname.lower()
    if varnamelc in alldatastatements:
        return ""
    alldatastatements.add(varnamelc)
    
    if vardict[varname].VariableLevel in ['nominal','ordinal']:
        unitcategory = iscat
    else:
        unitcategory = ""
    return datatemplate % {'varname': varname, "unitcategory": unitcategory}

def labelit(varname, vardict):
    """Return the variable label or, if none, the variable name
    
    varname is the variable to label.  If none, return ""
    vardict is a VariableDict object"""
    
    if not varname:
        return ""
    return vardict[varname].VariableLabel or varname
    
def scaling(numcharts, currentn, indent, yscale):
    """Return origin and scale GPL
    numcharts is the number of charts in this row
    currentn is the current chart number counting from zero
    indent is the indentation for the first chart in a row
    yscale is the percentage in the y dimension
    
    Assumes that this function is not called if only one chart per row
    and indent and yscale parameters are already validated."""
    
    xscale = (100. - indent) / numcharts
    xorigin = indent + (currentn * xscale)
    res = "origin(%(xorigin)s%%, 0%%), scale(%(xscale)s%%, %(yscale)s%%)" % locals()
    return res
    
        
def Run(args):
    """Execute the STATS REGRESS PLOT command"""

    args = args[args.keys()[0]]
    ###print args   #debug
    

    oobj = Syntax([
        Template("YVARS", subc="",  ktype="existingvarlist", var="yvars", islist=True),
        Template("XVARS", subc="",  ktype="existingvarlist", var="xvars", islist=True),
        Template("COLOR", subc="", ktype="existingvarlist", var="color"),
        Template("SIZE", subc="", ktype="existingvarlist", var="size"),
        Template("SHAPE", subc="",  ktype="existingvarlist", var="shape"),
        Template("LABEL", subc="", ktype="existingvarlist", var="label"),
        Template("LINEAR", subc="FITLINES", ktype="bool", var="linear"),
        Template("QUADRATIC", subc="FITLINES", ktype="bool", var="quadratic"),
        Template("CUBIC", subc="FITLINES", ktype="bool", var="cubic"),
        Template("LOESS", subc="FITLINES", ktype="bool", var="loess"),
        Template("IGNORE", subc="FITLINES", ktype="str", var="ignore"),
        Template("APPLYTO", subc="FITLINES", ktype="str", var="applyfitto", vallist=["total", "group"]),
        Template("CATEGORICAL", subc="OPTIONS", ktype="str", var="categorical", vallist=["bars", "lines", "boxplot"]),
        Template("GROUP", subc="OPTIONS", ktype="int", var="group"),
        Template("BOXPLOTS", subc="OPTIONS", ktype="bool", var="boxplots"),
        Template("HEXBIN", subc="OPTIONS", ktype="bool", var="hexbin"),
        Template("TITLE", subc="OPTIONS", ktype="literal", var="title"),
        Template("INDENT", subc="OPTIONS", ktype="int", var="indent", vallist=[0, 50]),
        Template("YSCALE", subc="OPTIONS", ktype="int", var="yscale", vallist=[50, 100]),
        Template("PAGEX", subc="OPTIONS", ktype="float", var="pagex", vallist=[1]),
        Template("PAGEY", subc="OPTIONS", ktype="float", var="pagey", vallist=[1]),
        Template("HELP", subc="", ktype="bool")])
    
        # ensure localization function is defined
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg

        # A HELP subcommand overrides all else
    if args.has_key("HELP"):
        #print helptext
        helper()
    else:
        processcmd(oobj, args, plots, vardict=spssaux.VariableDict())

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print("Help file not found:" + helpspec)            
try:    #override
    from extension import helper
except:
    pass
class NonProcPivotTable(object):
    """Accumulate an object that can be turned into a basic pivot table once a procedure state can be established"""
    
    def __init__(self, omssubtype, outlinetitle="", tabletitle="", caption="", rowdim="", coldim="", columnlabels=[],
                 procname="Messages"):
        """omssubtype is the OMS table subtype.
        caption is the table caption.
        tabletitle is the table title.
        columnlabels is a sequence of column labels.
        If columnlabels is empty, this is treated as a one-column table, and the rowlabels are used as the values with
        the label column hidden
        
        procname is the procedure name.  It must not be translated."""
        
        attributesFromDict(locals())
        self.rowlabels = []
        self.columnvalues = []
        self.rowcount = 0

    def addrow(self, rowlabel=None, cvalues=None):
        """Append a row labelled rowlabel to the table and set value(s) from cvalues.
        
        rowlabel is a label for the stub.
        cvalues is a sequence of values with the same number of values are there are columns in the table."""
        
        if cvalues is None:
            cvalues = []
        self.rowcount += 1
        if rowlabel is None:
            self.rowlabels.append(str(self.rowcount))
        else:
            self.rowlabels.append(rowlabel)
        if not spssaux._isseq(cvalues):
            cvalues = [cvalues]
        self.columnvalues.extend(cvalues)
        
    def generate(self):
        """Produce the table assuming that a procedure state is now in effect if it has any rows."""
        
        privateproc = False
        if self.rowcount > 0:
            try:
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            except:
                StartProcedure(_("Messages"), self.procname)
                privateproc = True
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            if self.caption:
                table.Caption(self.caption)
            # Note: Unicode strings do not work as cell values in 18.0.1 and probably back to 16
            if self.columnlabels != []:
                table.SimplePivotTable(self.rowdim, self.rowlabels, self.coldim, self.columnlabels, self.columnvalues)
            else:
                table.Append(spss.Dimension.Place.row,"rowdim",hideName=True,hideLabels=True)
                table.Append(spss.Dimension.Place.column,"coldim",hideName=True,hideLabels=True)
                colcat = spss.CellText.String("Message")
                for r in self.rowlabels:
                    cellr = spss.CellText.String(r)
                    table[(cellr, colcat)] = cellr
            if privateproc:
                spss.EndProcedure()
                
def attributesFromDict(d):
    """build self attributes from a dictionary d."""
    self = d.pop('self')
    for name, value in d.iteritems():
        setattr(self, name, value)
        
class Writelog(object):
    """Manage a log file"""
    
    def __init__(self, logfile):
        """logfile is the file name or None"""

        self.logfile = logfile
        if self. logfile:
            self.file = open(logfile, "w")
            self.starttime = time.time()
            self.file.write("%.2f %s Starting log\n" % (time.time() - self.starttime, time.asctime()))
            
    def __enter__(self):
        return self
    
    def write(self, text):
        if self.logfile:
            self.file.write("%.2f: %s\n" % (time.time() - self.starttime,  text))
            self.file.flush()
            
    def close(self):
        if self.logfile:
            self.write("Closing log")
            self.file.close()

def StartProcedure(procname, omsid):
    """Start a procedure
    
    procname is the name that will appear in the Viewer outline.  It may be translated
    omsid is the OMS procedure identifier and should not be translated.
    
    Statistics versions prior to 19 support only a single term used for both purposes.
    For those versions, the omsid will be use for the procedure name.
    
    While the spss.StartProcedure function accepts the one argument, this function
    requires both."""
    
    try:
        spss.StartProcedure(procname, omsid)
    except TypeError:  #older version
        spss.StartProcedure(omsid)