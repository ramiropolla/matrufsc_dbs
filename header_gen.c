#define _XOPEN_SOURCE 500
#include <stdio.h>
#include <inttypes.h>
#include <stdlib.h>

#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include <string.h>

#include <libxml/parser.h>
#include <libxml/tree.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <locale.h>
#include <iconv.h>
#include <errno.h>

#include <ctype.h>

iconv_t to_ascii;

static int has_started = 0;
static FILE *fp_fetch = NULL;
static FILE *fp_full = NULL;

static char *
strdup_to_ascii(char *string)
{
    char ascii_string[1024];
    char *i = string;
    char *o = ascii_string;
    char *p;
    size_t o_s = sizeof(ascii_string);
    size_t i_s = strlen(string)+1;
    int ret = iconv(to_ascii, &i, &i_s, &o, &o_s);
    if (ret == -1) {
        fprintf(stderr, "%s:%d some error with iconv '%s' %d\n", __FILE__, __LINE__, string, errno);
        exit(1);
    }
    p = ascii_string;
    while (*p) {
        *p = toupper(*p);
        p++;
    }
    return strdup(ascii_string);
}

static xmlNodePtr
get_child(xmlNodePtr parent, const char *name)
{
    xmlNodePtr child = parent->children;
    while (child) {
        if (!strcmp((const char *) child->name, name)) {
            return child;
        }
        child = child->next;
    }
    return NULL;
}

static char **
get_list(xmlNodePtr node)
{
    xmlNodePtr child;
    char **list;
    int l = 1, i = 0;
    for (child = node->children; child; child = child->next)
        if (child->type == 3 || (child->type == 1 && child->name[0] == 'a'))
            l++;
    list = malloc(l * sizeof(char *));
    for (child = node->children; child; child = child->next) {
        if (child->type == 1 && child->name[0] == 'a') {
            list[i++] = (char *) xmlNodeGetContent(child->children);
        } else if (child->type == 3) {
            list[i++] = (char *) xmlNodeGetContent(child);
        }
    }
    list[i] = NULL;
    return list;
}

static void
extract_turmas(const char *content, int length)
{
    xmlNodePtr node, tr;
    xmlDocPtr doc;

    doc = xmlReadMemory(content, length, "noname.xml", NULL, 0);
    if (doc == NULL) {
        fprintf(stderr, "Failed to parse document\n");
        return;
    }

    node = doc->children; /* <html> */
    node = get_child(node, "body");
    node = get_child(node, "table");
    node = get_child(node, "tbody");

    tr = node->children;
    while (tr) {
        static char lastc[10] = { 0 };
        struct {
            char *codigo_disciplina;
            char *nome_disciplina;
        } fetch;
        struct {
            char *codigo_disciplina;
            char *nome_turma;
            char *nome_disciplina;
            char *horas_aula;
            char *vagas_ofertadas;
            char *vagas_ocupadas;
            char *alunos_especiais;
            char *saldo_vagas;
            char *pedidos_sem_vaga;
            char **horarios;
            char **professores;
        } full;
        xmlNodePtr codigo_disciplina = tr->children->next->next->next;
        xmlNodePtr nome_turma        = codigo_disciplina->next;
        xmlNodePtr nome_disciplina   = nome_turma       ->next;
        xmlNodePtr horas_aula        = nome_disciplina  ->next;
        xmlNodePtr vagas_ofertadas   = horas_aula       ->next;
        xmlNodePtr vagas_ocupadas    = vagas_ofertadas  ->next;
        xmlNodePtr alunos_especiais  = vagas_ocupadas   ->next;
        xmlNodePtr saldo_vagas       = alunos_especiais ->next;
        xmlNodePtr pedidos_sem_vaga  = saldo_vagas      ->next;
        xmlNodePtr horarios          = pedidos_sem_vaga ->next;
        xmlNodePtr professores       = horarios         ->next;

        full.codigo_disciplina  = (char *) xmlNodeGetContent(codigo_disciplina->children);
        full.nome_turma         = (char *) xmlNodeGetContent(nome_turma       ->children);
        full.nome_disciplina    = (char *) xmlNodeGetContent(nome_disciplina  ->children);
        full.horas_aula         = (char *) xmlNodeGetContent(horas_aula       ->children);
        full.vagas_ofertadas    = (char *) xmlNodeGetContent(vagas_ofertadas  ->children);
        full.vagas_ocupadas     = (char *) xmlNodeGetContent(vagas_ocupadas   ->children);
        full.alunos_especiais   = (char *) xmlNodeGetContent(alunos_especiais ->children);
        full.saldo_vagas        = (char *) xmlNodeGetContent(saldo_vagas      ->children);
//        full.pedidos_sem_vaga   = (char *) xmlNodeGetContent(pedidos_sem_vaga );
        full.pedidos_sem_vaga   = (char *) "0";
        full.horarios           = get_list(horarios   );
        full.professores        = get_list(professores);

        fetch.codigo_disciplina = strdup_to_ascii(full.codigo_disciplina);
        fetch.nome_disciplina = strdup_to_ascii(full.nome_disciplina);


        if (strcmp(lastc, fetch.codigo_disciplina)) {
            fprintf(fp_fetch,
                "    { \"%s\", \"%s\", \"%s\" },\n",
                fetch.codigo_disciplina,
                fetch.nome_disciplina,
                full.nome_disciplina);

            if (has_started)
                fprintf(fp_full, "</materias>\" },\n");

            fprintf(fp_full, "    { \"%s\", \"", full.codigo_disciplina);
            fprintf(fp_full, "<materias>");
            fprintf(fp_full, "<codigo>%s</codigo>", full.codigo_disciplina);
            fprintf(fp_full, "<nome>%s</nome>", full.nome_disciplina);
            strcpy(lastc, fetch.codigo_disciplina);
            has_started = 1;
        }
        free(fetch.codigo_disciplina);
        free(fetch.nome_disciplina);

        fprintf(fp_full, "<turmas>");
        fprintf(fp_full, "<nome>%s</nome>", full.nome_turma);
        fprintf(fp_full, "<horas_aula>%s</horas_aula>", full.horas_aula);
        fprintf(fp_full, "<vagas_ofertadas>%s</vagas_ofertadas>", full.vagas_ofertadas);
        fprintf(fp_full, "<vagas_ocupadas>%s</vagas_ocupadas>", full.vagas_ocupadas);
        fprintf(fp_full, "<alunos_especiais>%s</alunos_especiais>", full.alunos_especiais);
        fprintf(fp_full, "<saldo_vagas>%s</saldo_vagas>", full.saldo_vagas);
        fprintf(fp_full, "<pedidos_sem_vaga>%s</pedidos_sem_vaga>", full.pedidos_sem_vaga);
        for (int j = 0; full.horarios[j]; j++)
            fprintf(fp_full, "<horarios>%s</horarios>", full.horarios[j]);
        for (int j = 0; full.professores[j]; j++)
            fprintf(fp_full, "<professores>%s</professores>", full.professores[j]);
        fprintf(fp_full, "</turmas>");

        tr = tr->next;
    }

    xmlFreeDoc(doc);
}

int main(int argc, char *argv[])
{
    const char *const start = "<?xml version=\"1.0\"?>";
    const int lstart = strlen(start);
    const char *const end = "------------------------------------------------------------------";
    const int lend = strlen(end);
    int start_at, end_at;
    const uint8_t *buf_in = NULL;
    char *fname_in = argv[1];
    struct stat st;
    int fd_in = 0;
    int ret = -1;

    LIBXML_TEST_VERSION

    if (argc < 4) {
        fprintf(stderr, "usage: %s <input> <fetch.h> <full.h>\n", argv[0]);
        goto end;
    }

    /* Open and mmap() input file */
    fd_in = open(fname_in, O_RDONLY);
    if (fd_in == -1) {
        fprintf(stderr, "could not open input file '%s'\n", fname_in);
        goto end;
    }
    if (fstat(fd_in, &st) == -1) {
        fprintf(stderr, "could not stat input file '%s'\n", fname_in);
        goto end;
    }
    buf_in = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd_in, 0);
    if (buf_in == MAP_FAILED) {
        fprintf(stderr, "could not map input file '%s'\n", fname_in);
        goto end;
    }

    fp_fetch = fopen(argv[2], "wb");
    if (!fp_fetch) {
        fprintf(stderr, "could not open output file '%s'\n", argv[2]);
        goto end;
    }
    fp_full = fopen(argv[3], "wb");
    if (!fp_full) {
        fprintf(stderr, "could not open output file '%s'\n", argv[3]);
        goto end;
    }

    fprintf(fp_fetch,
        "static struct {\n"
        "    char *codigo_disciplina;\n"
        "    char *nome_disciplina_ascii;\n"
        "    char *nome_disciplina_utf8;\n"
        "} fetch[] = {\n");
    fprintf(fp_full,
        "static struct {\n"
        "    char *codigo_disciplina;\n"
        "    char *result;\n"
        "} full[] = {\n");

    setlocale(LC_ALL, "en_US.utf8");

    to_ascii = iconv_open("ASCII//TRANSLIT", "utf8");
    if (to_ascii == (iconv_t) -1) {
        fprintf(stderr, "oh, bummer!\n");
        return -1;
    }

    for (int i = 0; i < st.st_size - lend; i++) {
        if        (!strncmp((char *) &buf_in[i], start, lstart)) {
            start_at = i;
        } else if (!strncmp((char *) &buf_in[i], end, lend)) {
            end_at = i;
            extract_turmas((char *) &buf_in[start_at], end_at - start_at);
        }
    }

    iconv_close(to_ascii);

    if (has_started)
        fprintf(fp_full, "</materias>\" },\n");
    fprintf(fp_full, "};\n");
    fprintf(fp_fetch, "};\n");

    ret = 0;

end:
    if (fp_fetch) fclose(fp_fetch);
    if (fp_full) fclose(fp_full);
    if (buf_in) munmap((void*)buf_in, st.st_size);
    if (fd_in ) close(fd_in);

    xmlCleanupParser();
    xmlMemoryDump();

    return ret;
}
