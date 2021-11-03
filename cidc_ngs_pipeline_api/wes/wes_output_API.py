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
    {
        "file_path": "analysis/align/{sample}/{sample}.sorted.dedup.bam",
        "short_descr": "alignment: bam file with deduplicated reads",
        "long_descr": "Aligned reads were sorted and marked duplicates were removed using the Sentieon Dedup tool (https://support.sentieon.com/manual/usages/general/#dedup-algorithm)",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },  # ALIGN
    {
        "file_path": "analysis/align/{sample}/{sample}.sorted.dedup.bam.bai",
        "short_descr": "alignment: bam index file for deduplicated bam",
        "long_descr": "Bam index file for deduplicated bam file generated by the Sentieon Dedup tool (https://support.sentieon.com/manual/usages/general/#dedup-algorithm)",
        "filter_group": "alignment",
        "file_purpose": "Source view",
    },
    {
        "file_path": "analysis/optitype/{sample}/{sample}_result.tsv",
        "short_descr": "hla: MHC Class I results (using OptiType)",
        "long_descr": "Predicted MHC Class I alleles using the Optitype software (https://github.com/FRED-2/OptiType).  Chromosome 6 reads from the deduplicated bam file were extracted and fed into the Optitype prediction algorithm.",
        "filter_group": "HLA",
    },  # HLA
    {
        "file_path": "analysis/xhla/{sample}/report-{sample}-hla.json",
        "short_descr": "hla: MHC Class I and II results (using xhla)",
        "long_descr": "Predicted MHC Class II and II results using the xHLA software(https://github.com/humanlongevity/HLA).  Chromosome 6 reads from the deduplicated bam file were extracted and fed into the xHLA prediction algorithm.",
        "filter_group": "HLA",
    },
    {
        "file_path": "analysis/metrics/{sample}/{sample}_coverage_metrics.txt",
        "short_descr": "coverage: global coverage file",
        "long_descr": "Genome wide coverage file generated using the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm) with a coverage threshold (cov_thresh) set to 50.",
        "filter_group": "coverage",
    },  # COVERAGE
    {
        "file_path": "analysis/metrics/{sample}/{sample}_target_metrics.txt",
        "short_descr": "coverage: target region coverage file",
        "long_descr": "Targeted exome regions coverage file using the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm) with a coverage threshold (cov_thresh) set to 50.",
        "filter_group": "coverage",
    },
    {
        "file_path": "analysis/metrics/{sample}/{sample}_coverage_metrics.sample_summary.txt",
        "short_descr": "coverage: global coverage summary file",
        "long_descr": "Genome wide coverage summary file generated by the Sentieon CoverageMetrics algorithm (https://support.sentieon.com/manual/usages/general/#coveragemetrics-algorithm).",
        "filter_group": "coverage",
    },
    {
        "file_path": "analysis/germline/{sample}/{sample}_haplotyper.targets.vcf.gz",
        "short_descr": "germline: vcf of haplotype variants in targeted regions",
        "long_descr": "Haplotype variants within targeted capture regions using Sentieon Haplotyper algorithm (https://support.sentieon.com/manual/usages/general/#haplotyper-algorithm)",
        "filter_group": "germline",
        "tumor_only_assay": False,
    },  # Germline
]

run_files = [
    {  # MISC
        "file_path": "analysis/{run}_error.yaml",
        "short_descr": "yaml file that specifies error codes for files",
        "long_descr": "Explanation of all files which are expected to be empty due to a failed/missing module.",
        "optional": True,  # optional
        "filter_group": "",
    },
    {  # SOMATIC
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.vcf.gz",
        "short_descr": "somatic variants: vcf file of somatic variants",
        "long_descr": """VCF file of somatic variants using one of the following the Sentieon somatic callers {tnscope (default), tnhaplotyper2, tnsnv}.

TNscope algorithm- https://support.sentieon.com/manual/usages/general/#tnscope-algorithm
TNhaplotyper2- https://support.sentieon.com/manual/usages/general/#tnhaplotyper2-algorithm
TNsnv - https://support.sentieon.com/manual/usages/general/#tnsnv-algorithm""",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.maf",
        "short_descr": "somatic variants: maf file of somatic variants",
        "long_descr": "MAF file of VEP annotated variants using vcf2maf tool (https://github.com/mskcc/vcf2maf).  The vep annotated vcf (output.vcf.gz) file was used as the input for vcf2maf.",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.filter.vcf.gz",
        "short_descr": "somatic variants: vcf file of filtered somatic variants",
        "long_descr": "VCF file of filtered somatic variants.  With the output.vcf file as input, the vcftools software was used with parameter --remove-filtered-all to remove any variants whose FILTER column is anything other than PASS.  see http://vcftools.sourceforge.net/man_latest.html",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.filter.maf",
        "short_descr": "somatic variants: maf file of filtered somatic variants",
        "long_descr": "MAF file of VEP annotated filtered variants using vcf2maf tool (https://github.com/mskcc/vcf2maf).  The filtered vep annotated vcf file (filter.vep.vcf) file was used as input for vcf2maf.",
        "filter_group": "somatic",
    },
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
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.optimized.vcf",
        "short_descr": "somatic variants: vcf file of somatic variants in TWIST targed capture region filtered by PASS column",
        "long_descr": "VCF file of variants that fall within the TWIST excome capture regions filtered to remove rows where the PASS column contained one of the following- germline-risk, low_t_alt_frac, t_lod_fstar, or triallelic_site",
        "filter_group": "somatic",
    },
    {
        "file_path": "analysis/somatic/{run}/{run}_{caller}.output.twist.optimized.maf",
        "short_descr": "somatic variants: maf file of somatic variants in TWIST targed capture region filtered by PASS column",
        "long_descr": "MAF file generated by converting twist.optimized.vcf to maf using VEP to annotate variants and vcf2maf to do the conversion.",
        "filter_group": "somatic",
    },
    #DEPRECATED by storing output.twist.vcf
    #{
    #    "file_path": "analysis/somatic/{run}/{run}_{caller}.filter.exons.center_targets.vcf.gz",
    #    "short_descr": "somatic variants: vcf file of filtered somatic variants from center target regions",
    #    "long_descr": "VCF file of filtered somatic variants from center target regions using bcftools (http://samtools.github.io/bcftools/bcftools.html).",
    #    "filter_group": "somatic",
    #},
    {
        "file_path": "analysis/germline/{run}/{run}_vcfcompare.txt",  # GERMLINE
        "short_descr": "somatic variants: overlap of somatic and germline variants",
        "long_descr": "VCFtool's vcf-compare (http://vcftools.sourceforge.net/perl_module.html#vcf-compare) is used to compare somatic and germline variants.  The file shows the number of common variants, somatic only, and germline only variants.",
        "filter_group": "somatic",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/report/somatic_variants/06_tumor_mutational_burden.tsv",
        "short_descr": "somatic variants: report file of tumor mutational burden in tumor and normal",
        "long_descr": "This file derived from the somatic and germline variants comparison results generated by vcf-compare (http://vcftools.sourceforge.net/perl_module.html#vcf-compare) and is formatted to be human readable.  The file reports the number of somatic/tumor only variants, germline/normal only variants, the number of shared variants, and the percent overlap (using the total number of somatic variants as the denominator).",
        "filter_group": "somatic",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/report/neoantigens/01_HLA_Results.tsv",  # HLA
        "short_descr": "hla: report file of combined MHC class I and II results",
        "long_descr": "This file reports the MHC class I and II results.  The class I alleles are derived from the OptiType results and the class II alleles come from the xHLA results. ",
        "filter_group": "HLA",
    },
    {
        "file_path": "analysis/neoantigen/{run}/combined/{run}.filtered.tsv",  # NEOANTI
        "short_descr": "neaontigen: list of predicted neoantigens",
        "long_descr": "The combined MHC class I and II predicted neoantigens using the pVACseq software.  The column definitions are given here (ref: https://pvactools.readthedocs.io/en/latest/pvacseq/output_files.html)",
        "filter_group": "neoantigen",
    },
    {
        "file_path": "analysis/purity/{run}/{run}.optimalpurityvalue.txt",  # PURITY
        "short_descr": "tumor purity: tumor purity analysis results",
        "long_descr": "Tumor purity calculations using the FACETS software (https://github.com/mskcc/facets)..",
        "filter_group": "purity",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_pyclone.tsv",  # CLONALITY
        "short_descr": "tumor clonality: PyClone input file generated by sequenza library (https://cran.r-project.org/web/packages/sequenza/index.html)",
        "long_descr": "Input file generated for PyClone analysis.  Sequenza was used to generate the expected file format (https://github.com/Roth-Lab/pyclone#input-format).",
        "filter_group": "clonality",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/clonality/{run}/{run}_table.tsv",
        "short_descr": "tumor clonality: tumor clonality analysis results",
        "long_descr": "Tumor clonality results using PyClone software (https://github.com/Roth-Lab/pyclone)..",
        "filter_group": "clonality",
        "tumor_only_assay": False,
    },
    {
        "file_path": "analysis/copynumber/{run}/{run}_cnvcalls.txt",  # CNV
        "short_descr": "copynumber: copynumber analysis results",
        "long_descr": "Copy number variation analysis results using Sentieon CNV algorithm (https://support.sentieon.com/appnotes/cnv/)",
        "filter_group": "copynumber",
    },
    {
        "file_path": "analysis/copynumber/{run}/{run}_cnvcalls.txt.tn.tsv",
        "short_descr": "copynumber: copynumber analysis results",
        "long_descr": "Segmented copy number variation file using Sentieon CNV algorithm (https://support.sentieon.com/appnotes/cnv/)",
        "filter_group": "copynumber",
    },
    {
        "file_path": "analysis/msisensor2/{run}/{run}_msisensor.txt",  # MSISENOR2
        "short_descr": "msisensor2: microsatellite instability calculation",
        "long_descr": "Microsatellite instability calculation using msisensor2 (https://github.com/niu-lab/msisensor2)",
        "filter_group": "msisensor2",
    },
    {
        "file_path": "analysis/rna/{run}/{run}.haplotyper.rna.vcf.gz",  # RNA
        "short_descr": "rna: Variants called from RNA-seq data",
        "long_descr": "RNA-seq variants called using the Sentieon RNA Variant Calling pipeline(https://support.sentieon.com/manual/RNA_call/rna/).  Sentieon's Haplotyper algorithm was used for the variant calling.",
        "filter_group": "rna",
        "optional": True,  # optional
    },
    {
        "file_path": "analysis/rna/{run}/{run}_{caller}.filter.neoantigen.vep.rna.vcf",
        "short_descr": "rna: Shared RNA and WES variants that is used for neoantigen prediction when RNA-seq data is provided with the WES run",
        "long_descr": "Variants file representing the common variants between RNA (haplotyper.rna.vcf.gz) and WES data (filter.neoantigen.vep.vcf).",
        "filter_group": "rna",
        "optional": True,  # optional
    },
    {
        "file_path": "analysis/report.tar.gz",  # REPORT
        "short_descr": "wes report: wes summary html report",
        "long_descr": "This is a gzipped file of the report directory, which contains the report.html file.  After unzipping the file, the user can load report/report.html into any browser to view the WES Summary Report.  The report contains run information (i.e. wes software version used to run the analysis as well as the software version of the major tools) as well as summarizations of sample quality, copy number variation, somatic variants, and HLA-type/neoantigen predictions.",
        "filter_group": "report",
    },
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
