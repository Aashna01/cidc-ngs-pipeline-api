#!/usr/bin/env python
"""Len Taing 2020 (TGBTG)"""

import os
import sys
import json
from optparse import OptionParser


class Wesfile:
    """General wes file object that will handle outputing to appropriate
    json API format"""

    def __init__(self, file_dict):
        """Given a file path, initializes this object to that path
        NOTE: filepath may include snakemake wildcards, e.g.
        analysis/germline/{run id}/{run id}_vcfcompare.txt"""
        # print(file_tuple)
        self.file_path_template = file_dict["file_path"]
        self.short_description = file_dict["short_descr"]
        self.long_description = file_dict["long_descr"]
        self.filter_group = file_dict["filter_group"]
        self.file_purpose = file_dict.get("file_purpose", "Analysis view")
        self.optional = file_dict.get("optional", False)
        self.tumor_only_assay = file_dict.get(
            "tumor_only_assay", True
        )  # default everything is part of tumor_only assay; below i mark this field false for normal files

    def __str__(self):
        return self.__dict__.__str__()


def dumper(obj):
    # ref: https://www.semicolonworld.com/question/42934/how-to-make-a-class-json-serializable
    try:
        return obj.toJSON()
    except:
        return obj.__dict__


def evalWildcards(file_tuple, wildcard, s, is_optional=False):
    # file_tuple[0] = file_tuple[0].replace(wildcard, s)
    # Non-destructive replacement
    # print(file_tuple)
    ret = file_tuple.copy()
    ret["file_path"] = ret["file_path"].replace(wildcard, s)
    return ret


sample_files = [
    ############################## ALIGN ##############################
    {
        "file_path": "analysis/align/{sample}/{sample}.sorted.dedup.bam",
        "short_descr": "alignment: bam file with deduplicated reads",
        "long_descr": "Aligned reads were sorted and marked duplicates were removed using the Sentieon Dedup tool (https://support.sentieon.com/manual/usages/general/#dedup-algorithm)",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },
    {
        "file_path": "analysis/align/{sample}/{sample}.sorted.dedup.bam.bai",
        "short_descr": "alignment: index file for deduplicated bam",
        "long_descr": "Bam index file for deduplicated bam file generated by the Sentieon Dedup tool (https://support.sentieon.com/manual/usages/general/#dedup-algorithm)",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },
    {
        "file_path": "analysis/align/{sample}/{sample}_recalibrated.bam",
        "short_descr": "alignment: Base Qualtiy Score Recalibration (BQSR) bam file",
        "long_descr": "The Sentieon QualCal (https://support.sentieon.com/manual/usages/general/#qualcal-algorithm) is used to perform BSQR and remove any technical artifacts in the base quality scores.",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },
    {
        "file_path": "analysis/align/{sample}/{sample}_recalibrated.bam.bai",
        "short_descr": "alignment: index file for Base Qualtiy Score Recalibration (BQSR) bam file",
        "long_descr": "Index file for the BQSR bam file",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },
    ############################## germline ##############################
    # NOTE: we're ingesting both tumor and normal samples germline call, but
    # the one that only counts is the normal sample's germline call
    {
        "file_path": "analysis/germline/{sample}/{sample}_haplotyper.output.vcf",
        "short_descr": "germline: germline variants",
        "long_descr": "Haplotype variants using Sentieon Haplotyper algorithm (https://support.sentieon.com/manual/usages/general/#haplotyper-algorithm)",
        "filter_group": "germline",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/germline/{sample}/{sample}_haplotyper.targets.vcf.gz",
        "short_descr": "germline: vcf of haplotype variants in targeted regions",
        "long_descr": "Haplotype variants within targeted capture regions using Sentieon Haplotyper algorithm (https://support.sentieon.com/manual/usages/general/#haplotyper-algorithm)",
        "filter_group": "germline",
        "tumor_only_assay": False,
    },
    ###################################################################
    # NOTE: FOR all hla callers we're ingesting both tumor and normal
    # sample, but the one that counts is the tumor sample's
    #
    # ALSO: for hla, we're not stashing the chr6 fastqs (which are used
    # as input for the HLA callers b/c those can be quickly re-derived
    # from sorted.dedup.bam --under 30secs per sample)
    ############################## hlahd ##############################
    {
        "file_path": "analysis/hlahd/{sample}/result/{sample}_final.result.txt",
        "short_descr": "hla: MHC Class I and II results (using HLA-HD)",
        "long_descr": "Predicted MHC Class II and II results using the HLA-HD software (https://www.genome.med.kyoto-u.ac.jp/HLA-HD/).  Chromosome 6 reads from the deduplicated bam file were extracted and fed into the HLA-HD prediction algorithm.",
        "filter_group": "HLA",
    },
    ############################## optitype #######################
    {
        "file_path": "analysis/optitype/{sample}/{sample}_result.tsv",
        "short_descr": "hla: MHC Class I results (using OptiType)",
        "long_descr": "Predicted MHC Class I alleles using the Optitype software (https://github.com/FRED-2/OptiType).  Chromosome 6 reads from the deduplicated bam file were extracted and fed into the Optitype prediction algorithm.",
        "filter_group": "HLA",
    },
    ############################## xhla #######################
    {
        "file_path": "analysis/xhla/{sample}/report-{sample}-hla.json",
        "short_descr": "hla: MHC Class I and II results (using xhla)",
        "long_descr": "Predicted MHC Class I and II results using the xHLA software(https://github.com/humanlongevity/HLA).  Chromosome 6 reads from the deduplicated bam file were extracted and fed into the xHLA prediction algorithm.",
        "filter_group": "HLA",
    },
    #####################################################################
    # 2022-06-14 DEPRECATING ALL metrics for ingestion for the following
    # reasons:
    # 1. They are BIG and USELESS (we have never looked at them)
    # 2. the sample's summary coverage, e.g. total_reads, mean_depth,
    #    percent_bases_gt_50, etc. are sufficient in 99.9% of the cases!
    # 3. since we are stashing the sorted.dedup.bam file, we can always
    #    re-derive them IF we need!
    ############################## metrics ##############################
    # {
    #     "file_path": "analysis/metrics/{sample}/{sample}_coverage_metrics.txt",
    #     "short_descr": "coverage: global coverage file",
    #     "long_descr": "Genome wide coverage file generated using the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm) with a coverage threshold (cov_thresh) set to 50.",
    #     "filter_group": "coverage",
    # },
    # {
    #     "file_path": "analysis/metrics/{sample}/{sample}_target_metrics.txt",
    #     "short_descr": "coverage: target region coverage file",
    #     "long_descr": "Targeted exome regions coverage file using the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm) with a coverage threshold (cov_thresh) set to 50.",
    #     "filter_group": "coverage",
    # },
    # {
    #     "file_path": "analysis/metrics/{sample}/{sample}_coverage_metrics.sample_summary.txt",
    #     "short_descr": "coverage: global coverage summary file",
    #     "long_descr": "Genome wide coverage summary file generated by the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm).",
    #     "filter_group": "coverage",
    # },
]

run_files = [
    ############################## MISC ##############################
    {
        "file_path": "analysis/{run}_error.yaml",
        "short_descr": "yaml file that specifies error codes for files",
        "long_descr": "Explanation of all files which are expected to be empty due to a failed/missing module.",
        "optional": True,  # optional
        "filter_group": "",
    },
    ############################## clonality ##############################
    # sequenza files
    {
        "file_path": "analysis/clonality/{run}/{run}_segments.txt",
        "short_descr": "copynumber: Sequenza CNV segments file",
        "long_descr": "Copy number variation segments file called by the Sequenza software package.  The column descriptions for the segment file could be found here (https://cran.r-project.org/web/packages/sequenza/vignettes/sequenza.html#plots-and-results)",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_genome_view.pdf",
        "short_descr": "copynumber: Sequenza genome-wide plot of depth.ratio and B-allele frequency.",
        "long_descr": "Genome-wide plot (generated by Sequenza) showing depth.ratio and B-allele frequency.",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_chromosome_view.pdf",
        "short_descr": "copynumber: Sequenza plot of depth.ratio and B-allele frequency chromosome by chromosome.",
        "long_descr": "Chromosome by chromosome plot (generated by Sequenza) showing depth.ratio and B-allele frequency.",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_sequenza_gainLoss.bed",
        "short_descr": "copynumber: Sequenza CNV segments file filtered with hard cut-offs to call regions of GAIN/LOSS",
        "long_descr": "Filtered Sequenza segments file after applying a hard cut-off to call regions of GAIN (total copy number >= 3) and regions of LOSS (total copy number <= 1.5).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    ######################################################################
    # NOTE: stashing final.seqz file because it's 1. SMALL (under 100MB)
    #       and 2. is very hard to re-derive from recalibrated.bam
    ######################################################################
    {
        "file_path": "analysis/clonality/{run}/{run}.bin50.final.seqz.txt.gz",
        "short_descr": "copynumber: Sequenza post-processed seqz file used for input to Sequenza CNV caller",
        "long_descr": "Sequenza seqz file generated by the bam2seqz software using a GC wiggle track with a window size of 50 (-w 50).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    # purity files
    {
        "file_path": "analysis/clonality/{run}/{run}_alternative_solutions.txt",
        "short_descr": "purity: Sequenza Cellularity and Ploidy estimate file",
        "long_descr": "Cellularity and ploidy estimates of the tumor sample using the Sequenza software package.  The columns of the file are follows: Cellularity, Ploidy, and SLPP (Scaled Log Posterior Probability).",
        "filter_group": "purity",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_CP_contours.pdf",
        "short_descr": "purity: Sequenza plot of likelihood densities for all cellularity/ploidy solutions.",
        "long_descr": "Sequenza generated plot showing the likelihood densities for each cellularity/ploidy solution (https://cran.r-project.org/web/packages/sequenza/vignettes/sequenza.html#plots-and-results).",
        "filter_group": "purity",
        "tumor_only_assay": False,
    },
    # pyclone files
    {
        "file_path": "analysis/clonality/{run}/{run}_pyclone6.input.tsv",
        "short_descr": "tumor clonality: PyClone-VI input file generated by sequenza library (https://cran.r-project.org/web/packages/sequenza/index.html)",
        "long_descr": "Input file generated for PyClone-VI analysis.  Sequenza was used to generate the expected file format (https://github.com/Roth-Lab/pyclone-vi#input-format).",
        "filter_group": "clonality",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_pyclone6.results.tsv",
        "short_descr": "tumor clonality: PyClone-VI tumor clonality results file",
        "long_descr": "Tumor clone/cluster prevalence estimations generated by the PyClone-VI software package.  The format of the results file is described here (https://github.com/Roth-Lab/pyclone-vi#output-format).",
        "filter_group": "clonality",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_pyclone6.results.summary.tsv",
        "short_descr": "tumor clonality: PyClone-VI tumor clonality results summary file",
        "long_descr": "Summary of Pyclone-VI results file condensed to only show the cluster_id, cellular_prevalence, and cellular_prevalence_std columns.",
        "filter_group": "clonality",
        "tumor_only_assay": False,
    },
    ############################## CNVkit ##############################
    {
        "file_path": "analysis/cnvkit/{run}/{run}.call.cns",
        "short_descr": "copynumber: CNVkit segments file",
        "long_descr": "CNVkit's Segmented log2 ratios file. The 'cn' column representes the total copy number of the segment.  The other columns of the results file are described here (https://cnvkit.readthedocs.io/en/stable/fileformats.html#segmented-log2-ratios-cns)",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/cnvkit/{run}/{run}.call.enhanced.cns",
        "short_descr": "copynumber: Enhanced CNVkit segments file with BAF and Major/minor allele information",
        "long_descr": "The enhanced CNVkit segments file incoporates somatic sNP and tumor purity information (called by the pipeline) to incorporate B-allele frequencies, major and minor allele (cn1 and cn2 respectively), and correct for tumor sample purity level.",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/cnvkit/{run}/{run}.scatter.png",
        "short_descr": "copynumber: scatter plot of log2 coverage and segmentation call information",
        "long_descr": "Genome-wide scatter plot of log2 coverage ratios and called CNV segments",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/cnvkit/{run}/{run}_cnvkit_gainLoss.bed",
        "short_descr": "copynumber: CNVkit segments file filtered with hard cut-offs to call regions of GAIN/LOSS",
        "long_descr": "Filtered CNVkit segments file after applying a hard cut-off to call regions of GAIN (total copy number >= 3) and regions of LOSS (total copy number <= 1.5).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    ############################## Copynumber ##############################
    {
        "file_path": "analysis/copynumber/{run}/{run}_consensus.bed",
        "short_descr": "copynumber: Consensus CNV segments file",
        "long_descr": "Consensus CNV regions that are called by at least 2 of the 3 callers (CNVkit, Sequenza, or FACETS).  CNV Callers must agree on both the region (intersection of overlapped regions) and the call (GAIN or LOSS).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/copynumber/{run}/{run}_consensus_merged_GAIN.bed",
        "short_descr": "copynumber: Consensus CNV segments file of only GAIN regions",
        "long_descr": "GAIN only CNV regions derived from the consensus CNV file.  Regions are also merged if they have an overlap of at least 1bp. ",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/copynumber/{run}/{run}_consensus_merged_LOSS.bed",
        "short_descr": "copynumber: Consensus CNV segments file of only LOSS regions",
        "long_descr": "LOSS only CNV regions derived from the consensus CNV file.  Regions are also merged if they have an overlap of at least 1bp. ",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    ############################## msisensor2 ##############################
    {
        "file_path": "analysis/msisensor2/{run}/{run}_msisensor2.txt",
        "short_descr": "msisensor2: microsatellite instability calculation",
        "long_descr": "Microsatellite instability calculation using msisensor2 (https://github.com/niu-lab/msisensor2)",
        "filter_group": "msisensor2",
    },
    ############################## neoantigen ##############################
    {
        "file_path": "analysis/neoantigen/{run}/combined/{run}.filtered.tsv",
        "short_descr": "neaontigen: list of predicted neoantigens",
        "long_descr": "The combined MHC class I and II predicted neoantigens using the pVACseq software.  The column definitions are given here (ref: https://pvactools.readthedocs.io/en/latest/pvacseq/output_files.html)",
        "filter_group": "neoantigen",
    },
    ############################## purity ##############################
    {
        "file_path": "analysis/purity/{run}/{run}.optimalpurityvalue.txt",
        "short_descr": "tumor purity: tumor purity estimates using the FACETS software package",
        "long_descr": "Tumor purity estimates using the FACETS software (https://github.com/mskcc/facets).",
        "filter_group": "purity",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/purity/{run}/{run}.cncf",
        "short_descr": "copynumber: FACETS CNV segments file",
        "long_descr": "Copy number variation segments file called by the FACETS software (https://github.com/mskcc/facets).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/purity/{run}/{run}_facets_gainLoss.bed",
        "short_descr": "copynumber: FACETS CNV segments file filtered with hard-cutoff to call regions of GAIN/LOSS",
        "long_descr": "Filtered FACETS segments file after applying a hard cut-off to call regions of GAIN (total copy number >= 3) and regions of LOSS (total copy number <= 1.5).",
        "filter_group": "copynumber",
        "tumor_only_assay": False,
    },
    ############################## report ##############################
    {
        "file_path": "analysis/report.tar.gz",
        "short_descr": "wes report: wes summary html report",
        "long_descr": "This is a gzipped file of the report directory, which contains the report.html file.  After unzipping the file, the user can load report/report.html into any browser to view the WES Summary Report.  The report contains run information (i.e. wes software version used to run the analysis as well as the software version of the major tools) as well as summarizations of sample quality, copy number variation, somatic variants, and HLA-type/neoantigen predictions.",
        "filter_group": "report",
    },
    {
        "file_path": "analysis/report/somatic_variants/05_tumor_germline_overlap.tsv",
        "short_descr": "somatic variants: report file of tumor vs germline variants overlap",
        "long_descr": "This file derived from the somatic and germline variants comparison results generated by vcf-compare (http://vcftools.sourceforge.net/perl_module.html#vcf-compare) and is formatted to be human readable.  The file reports the number of somatic/tumor only variants (unfiltered), germline/normal only variants (unfiltered), the number of shared variants, and the percent overlap (using the total number of somatic variants as the denominator).",
        "filter_group": "somatic",
        "tumor_only_assay": False,
    },
    # DEPRECATED! b/c we have 3 other HLA files!
    # {
    #     "file_path": "analysis/report/neoantigens/01_HLA_Results.tsv",  # HLA
    #     "short_descr": "hla: report file of combined MHC class I and II results",
    #     "long_descr": "This file reports the MHC class I and II results.  The class I alleles are derived from the OptiType results and the class II alleles come from the HLA-HD results. ",
    #     "filter_group": "HLA",
    # },
    {
        "file_path": "analysis/report/WES_Meta/02_WES_Run_Version.tsv",
        "short_descr": "wes pipeline version- INTERNAL ONLY- for reproducibility",
        "long_descr": "wes pipeline version- INTERNAL ONLY- for reproducibility",
        "filter_group": "report",
        "file_purpose": "Miscellaneous",
    },
    {
        "file_path": "analysis/report/config.yaml",
        "short_descr": "wes pipeline config file- INTERNAL ONLY- for reproducibility",
        "long_descr": "wes pipeline config file- INTERNAL ONLY- for reproducibility",
        "filter_group": "report",
        "file_purpose": "Miscellaneous",
    },
    {
        "file_path": "analysis/report/metasheet.csv",
        "short_descr": "wes pipeline metasheet file- INTERNAL ONLY- for reproducibility",
        "long_descr": "wes pipeline metasheet file- INTERNAL ONLY- for reproducibility",
        "filter_group": "report",
        "file_purpose": "Miscellaneous",
    },
    {
        "file_path": "analysis/report/json/{run}.wes.json",
        "short_descr": "wes sample json for cohort report generation-INTERNAL ONLY",
        "long_descr": "wes sample json for cohort report generation-INTERNAL ONLY",
        "filter_group": "report",
        "file_purpose": "Miscellaneous",
    },
    ############################## rna ##############################
    {
        "file_path": "analysis/rna/{run}/{run}.haplotyper.rna.vcf.gz",  # RNA
        "short_descr": "rna: Variants called from RNA-seq data",
        "long_descr": "RNA-seq variants called using the Sentieon RNA Variant Calling pipeline(https://support.sentieon.com/manual/RNA_call/rna/).  Sentieon's Haplotyper algorithm was used for the variant calling.",
        "filter_group": "rna",
        "optional": True,  # optional
    },
    {
        "file_path": "analysis/rna/{run}/{run}_{caller}.output.twist.neoantigen.vep.rna.vcf",
        "short_descr": "rna: Shared RNA and WES variants that is used for neoantigen prediction when RNA-seq data is provided with the WES run",
        "long_descr": "Variants file representing the common variants between RNA (haplotyper.rna.vcf.gz) and WES data (output.twist.neoantigen.vep.vcf).",
        "filter_group": "rna",
        "optional": True,  # optional
    },
    ############################## somatic ##############################
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.vcf.gz",
        "short_descr": "somatic variants: vcf file of somatic variants",
        "long_descr": """VCF file of somatic variants using one of the following the Sentieon somatic callers {tnscope (default), tnhaplotyper2, tnsnv}.

TNscope algorithm- https://support.sentieon.com/manual/usages/general/#tnscope-algorithm
TNhaplotyper2- https://support.sentieon.com/manual/usages/general/#tnhaplotyper2-algorithm
TNsnv - https://support.sentieon.com/manual/usages/general/#tnsnv-algorithm""",
        "filter_group": "somatic",
    },
    # another way of describing it way of doing it
    # {
    #     "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.vcf",
    #     "short_descr": "somatic variants: vcf file of somatic variants in TWIST targeted capture regions",
    #     "long_descr": "VCF file of somatic variants that are within the TWIST exome capture regions.  bcftools is used to filter reads in output.vcf.gz that intersect with the TWIST capture regions.",
    #     "filter_group": "somatic",
    # },
    # {
    #     "file_path": "analysis/somatic/{run}/{run}_{caller}.twist.maf",
    #     "short_descr": "somatic variants: maf file of somatic variants in TWIST targeted capture regions",
    #     "long_descr": "MAF file of TWIST variants using vcf2maf tool (https://github.com/mskcc/vcf2maf).  The vep annotated vcf of the TWIST variants (output.twist.vcf) was converted to maf using vcf2maf.",
    #     "filter_group": "somatic",
    # },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.vcf",
        "short_descr": "somatic variants: vcf file of somatic variants in TWIST targed capture region",
        "long_descr": "VCF file of variants that fall within the TWIST excome capture regions.  bcftools is used to filter reads in output.vcf.gz that intersect with the TWIST capture regions.",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.maf",
        "short_descr": "somatic variants: maf file of somatic variants in TWIST targed capture region",
        "long_descr": "MAF file of variants that fall within the TWIST excome capture regions generated using vcf2maf tool (https://github.com/mskcc/vcf2maf). VEP was used to annotate twist.vcf file, which was then used as input to vcf2maf.",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.filtered.vcf",
        "short_descr": "somatic variants: vcf file of somatic variants in TWIST targed capture region filtered by PASS column",
        "long_descr": "VCF file of variants that fall within the TWIST excome capture regions filtered to remove vairants where the PASS column contained one of the following- germline-risk, low_t_alt_frac, t_lod_fstar, or triallelic_site",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.filtered.maf",
        "short_descr": "somatic variants: maf file of somatic variants in TWIST targed capture region filtered by PASS column",
        "long_descr": "MAF file generated by converting twist.filtered.vcf to maf using VEP to annotate variants and vcf2maf to do the conversion.",
        "filter_group": "somatic",
    },
    ############################## tcellextrect ##############################
    {
        "file_path": "analysis/tcellextrect/{run}/{run}_tcellextrect.txt",
        "short_descr": "tcell: TCell fraction estimates generated by TcellExTRECT",
        "long_descr": "TCell fraction estimates generated by the TcellExTRECT software (https://github.com/McGranahanLab/TcellExTRECT)",
        "filter_group": "tcell",
    },
    # DEPRECATED by storing output.twist.vcf
    # {
    #    "file_path": "analysis/somatic/{run}/{run}_{caller}.filter.exons.center_targets.vcf.gz",
    #    "short_descr": "somatic variants: vcf file of filtered somatic variants from center target regions",
    #    "long_descr": "VCF file of filtered somatic variants from center target regions using bcftools (http://samtools.github.io/bcftools/bcftools.html).",
    #    "filter_group": "somatic",
    # },
    # DEPRECATED b/c we already have report/somatic_variants/05_tumor_germline_overlap.tsv",
    # {
    #     "file_path": "analysis/germline/{run}/{run}_vcfcompare.txt",  # GERMLINE
    #     "short_descr": "somatic variants: overlap of somatic and germline variants",
    #     "long_descr": "VCFtool's vcf-compare (http://vcftools.sourceforge.net/perl_module.html#vcf-compare) is used to compare somatic and germline variants.  The file shows the number of common variants, somatic only, and germline only variants.",
    #     "filter_group": "somatic",
    #     "tumor_only_assay": False,
    # },
    # DEPRECATED b/c sentieon cnv caller is removed
    # {
    #     "file_path": "analysis/copynumber/{run}/{run}_cnvcalls.txt",  # CNV
    #     "short_descr": "copynumber: copynumber analysis results",
    #     "long_descr": "Copy number variation analysis results using Sentieon CNV algorithm (https://support.sentieon.com/appnotes/cnv/)",
    #     "filter_group": "copynumber",
    # },
    # {
    #     "file_path": "analysis/copynumber/{run}/{run}_cnvcalls.txt.tn.tsv",
    #     "short_descr": "copynumber: copynumber analysis results",
    #     "long_descr": "Segmented copy number variation file using Sentieon CNV algorithm (https://support.sentieon.com/appnotes/cnv/)",
    #     "filter_group": "copynumber",
    # },
]


def main():
    usage = "USAGE: %prog -t [tumor_only assay files (default: False--prints tumor/normal assay files)"
    optparser = OptionParser(usage=usage)
    optparser.add_option(
        "-t",
        "--tumor_only",
        help="print files for tumor_only assay (default: False)",
        default=False,
        action="store_true",
    )
    (options, args) = optparser.parse_args(sys.argv)

    run_id_files = [
        r for r in map(lambda x: evalWildcards(x, "{run}", "{run id}"), run_files)
    ]
    run_id_files = [
        Wesfile(r)
        for r in map(lambda x: evalWildcards(x, "{caller}", "tnscope"), run_id_files)
    ]

    normal_files = [
        Wesfile(s)
        # NOTE: sending in the is_optional param: True for evalWildcards for normal samples
        for s in map(
            lambda x: evalWildcards(x, "{sample}", "{normal cimac id}", True),
            sample_files,
        )
    ]
    # Will remove normals below IF options.tumor_only is True
    #    #remove normal files from tumor_only_assay
    #    for nf in normal_files:
    #        nf.tumor_only_assay = False

    tumor_files = [
        Wesfile(s)
        for s in map(
            lambda x: evalWildcards(x, "{sample}", "{tumor cimac id}"), sample_files
        )
    ]

    tmp = {
        "run id": run_id_files,
        "normal cimac id": normal_files,
        "tumor cimac id": tumor_files,
    }

    if options.tumor_only:  # REMOVE normal files for tumor_only assay
        del tmp["normal cimac id"]
        # also remove any item that is marked tumor_only_assay
        tmp["run id"] = list(
            filter(lambda x: getattr(x, "tumor_only_assay"), tmp["run id"])
        )
        tmp["tumor cimac id"] = list(
            filter(lambda x: getattr(x, "tumor_only_assay"), tmp["tumor cimac id"])
        )
        output_f = "wes_tumor_only_output_API.json"
    else:
        output_f = "wes_output_API.json"

    # DUMP the file
    json.dump(
        tmp,
        open(os.path.join(os.path.dirname(__file__), output_f), "w"),
        default=dumper,
        indent=4,
    )
    # print(json.dumps(tmp, default=dumper, indent=4))


if __name__ == "__main__":
    main()
